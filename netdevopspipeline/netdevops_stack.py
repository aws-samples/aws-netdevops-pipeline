from aws_cdk import Stack
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import pipelines as cdk_pipeline
from aws_cdk import Fn
from aws_cdk import aws_iam as iam
from netdevopspipeline.pipeline_stage.DevHubFoundationInfraStage import DevHubFoundationInfraStage
from netdevopspipeline.pipeline_stage.ProdHubFoundationInfraStage import ProdHubFoundationInfraStage
from netdevopspipeline.pipeline_stage.DevHubInfraStage import DevHubInfraStage
from netdevopspipeline.pipeline_stage.DevSpokeInfraStage import DevSpokeInfraStage
from netdevopspipeline.pipeline_stage.ProdHubInfraStage import ProdHubInfraStage
from netdevopspipeline.pipeline_stage.ProdSpokeInfraStage import ProdSpokeInfraStage
from netdevopspipeline.pipeline_stage.DevValidationStage import ValidationStage
import netdevopspipeline.accounts

from constructs import Construct


class NetDevopsPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get Context values to be passed as variable

        Security_findings_lambda = self.node.try_get_context("security_hub_lambda")
        Hub_cidr = self.node.try_get_context("cidr_hub")
        Hub_dr_cidr = self.node.try_get_context("cidr_hub_dr")
        Spoke_cidr = self.node.try_get_context("cidr_spoke")
        Spoke_dr_cidr = self.node.try_get_context("cidr_spoke_dr")
        pipeline_approver_sns = self.node.try_get_context("sns_topic")

        # sns topic arn for validation
        approver_topic_arn = f"arn:aws:sns:{netdevopspipeline.accounts.Development_ENV.region}:{netdevopspipeline.accounts.Development_ENV.account}:{pipeline_approver_sns}"

        repository = codecommit.Repository.from_repository_name(
            self, "repo_name", Fn.import_value("netdevopsrepo")
        )

        self.pipeline = cdk_pipeline.CodePipeline(
            self,
            "cdkpipeline",
            cross_account_keys=True,
            synth=cdk_pipeline.CodeBuildStep(
                "synth-and-deployment-validation",
                input=cdk_pipeline.CodePipelineSource.code_commit(repository, "main"),
                commands=[
                    "npm install -g aws-cdk",
                    "pip install -r requirements.txt",
                    "cdk synth",
                    "pytest tests",
                    "gem install cfn-nag",
                    f"infra_findings_lambda={Security_findings_lambda}",
                    "failed_checks=$(cfn_nag_scan -g -i ./cdk.out/ -o json --profile-path ./profile.txt | jq \".[] | select (.file_results.violations != [])\" | wc -l)",
                    "if [ $failed_checks -gt 0 ]; then cfn_nag_scan -g -i ./cdk.out/ -o json --profile-path ./profile.txt | jq \".[] | select (.file_results.violations != [])\" > cfn_nag_findings.json && jq -s . cfn_nag_findings.json > cfn_report.json && jq \"{ \\\"messageType\\\": \\\"CfnNagScanReport\\\", \\\"reportType\\\": \\\"CfnNag-scan\\\", \\\"createdAt\\\": \\\"$(date +\"%Y-%m-%dT%H:%M:%S.%3NZ\")\\\", \\\"report\\\": . }\" cfn_report.json > payload.json && aws lambda invoke --function-name $infra_findings_lambda --payload file://payload.json --cli-binary-format raw-in-base64-out cfn_report.json && exit 1; else exit 0; fi"
                ],
                role_policy_statements=[
                    iam.PolicyStatement(
                        actions=["ec2:DescribeAvailabilityZones"],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        actions=["lambda:InvokeFunction"],
                        resources=[f"arn:aws:lambda:{netdevopspipeline.accounts.Development_ENV.region}:{netdevopspipeline.accounts.Development_ENV.account}:function:{Security_findings_lambda}"],
                    ),
                    iam.PolicyStatement(
                        actions=["sts:AssumeRole"],
                        resources=["*"],
                        conditions={
                            "StringEquals": {
                                "iam:ResourceTag/aws-cdk:bootstrap-role": "lookup"
                            }
                        }
                    )
                ]
            )
        )

        Dev_Hub_Foundation_stage = DevHubFoundationInfraStage(self, "DevFoundationStage",env=netdevopspipeline.accounts.Dev_Hub_Primary_ENV)
        self.pipeline.add_stage(Dev_Hub_Foundation_stage)

        # The Dev stages to run parallel in Primary and DR region the wave configuration is set. 
        Dev_Hub_Wave = self.pipeline.add_wave("dev_hub")
        Dev_Spoke_Wave = self.pipeline.add_wave("dev_spoke")
        Dev_Validate_Wave = self.pipeline.add_wave("dev_validate")

        Prod_Hub_Foundation_stage = ProdHubFoundationInfraStage(self, "ProdFoundationStage", env=netdevopspipeline.accounts.Prod_Hub_Primary_ENV)
        self.pipeline.add_stage(Prod_Hub_Foundation_stage, pre=cdk_pipeline.Step.sequence([cdk_pipeline.ManualApprovalStep("PromoteToProd")]))

        # The Prod stage to run parallel in Primary and DR region the wave configuration is set.
        Prod_Hub_Wave = self.pipeline.add_wave("prod_hub")
        Prod_Spoke_Wave = self.pipeline.add_wave("prod_spoke")

        Dev_Hub_stage = DevHubInfraStage(self, "DevHubStage-PrimaryRegion", cidr=Hub_cidr, dr_cidr=Spoke_cidr, region=netdevopspipeline.accounts.Dev_Hub_Primary_ENV.region, env=netdevopspipeline.accounts.Dev_Hub_Primary_ENV)
        Dev_Hub_Wave.add_stage(Dev_Hub_stage)

        Dev_Hub_DR_stage = DevHubInfraStage(self, "DevHubStage-DrRegion", cidr=Hub_dr_cidr, dr_cidr=Spoke_dr_cidr, region=netdevopspipeline.accounts.Dev_Hub_Dr_ENV.region, env=netdevopspipeline.accounts.Dev_Hub_Dr_ENV)
        Dev_Hub_Wave.add_stage(Dev_Hub_DR_stage)
        
        Dev_Spoke_stage = DevSpokeInfraStage(self, "DevSpokeStage-PrimaryRegion", cidr=Spoke_cidr, env=netdevopspipeline.accounts.Dev_Spoke_Primary_ENV)
        Dev_Spoke_Wave.add_stage(Dev_Spoke_stage)

        Dev_Spoke_DR_stage = DevSpokeInfraStage(self, "DevSpokeStage-DrRegion", cidr=Spoke_dr_cidr, env=netdevopspipeline.accounts.Dev_Spoke_Dr_ENV)
        Dev_Spoke_Wave.add_stage(Dev_Spoke_DR_stage)

        Dev_validation_stage = ValidationStage(self, "DevValidateStage-PrimaryRegion", topic_arn=approver_topic_arn, Dev_account_region=netdevopspipeline.accounts.Development_ENV.region,env=netdevopspipeline.accounts.Dev_Hub_Primary_ENV)
        Dev_Validate_Wave.add_stage(Dev_validation_stage)

        Dev_DR_validation_stage = ValidationStage(self, "DevValidateStage-DrRegion", topic_arn=approver_topic_arn, Dev_account_region=netdevopspipeline.accounts.Development_ENV.region ,env=netdevopspipeline.accounts.Dev_Hub_Dr_ENV)
        Dev_Validate_Wave.add_stage(Dev_DR_validation_stage)
    
        Prod_Hub_stage = ProdHubInfraStage(self, "ProdHubStage-PrimaryRegion", cidr=Hub_cidr, dr_cidr=Spoke_cidr, region=netdevopspipeline.accounts.Prod_Hub_Primary_ENV.region, env=netdevopspipeline.accounts.Prod_Hub_Primary_ENV)
        Prod_Hub_Wave.add_stage(Prod_Hub_stage)

        Prod_Hub_DR_stage = ProdHubInfraStage(self, "ProdHubStage-DrRegion", cidr=Hub_dr_cidr, dr_cidr=Spoke_dr_cidr, region=netdevopspipeline.accounts.Prod_Hub_Dr_ENV.region, env=netdevopspipeline.accounts.Prod_Hub_Dr_ENV)
        Prod_Hub_Wave.add_stage(Prod_Hub_DR_stage)
        
        Prod_Spoke_stage = ProdSpokeInfraStage(self, "ProdSpokeStage-PrimaryRegion", cidr=Spoke_cidr, env=netdevopspipeline.accounts.Prod_Spoke_Primary_ENV)
        Prod_Spoke_Wave.add_stage(Prod_Spoke_stage)

        Prod_Spoke_DR_stage = ProdSpokeInfraStage(self, "ProdSpokeStage-DrRegion", cidr=Spoke_dr_cidr, env=netdevopspipeline.accounts.Prod_Spoke_Dr_ENV)
        Prod_Spoke_Wave.add_stage(Prod_Spoke_DR_stage)


