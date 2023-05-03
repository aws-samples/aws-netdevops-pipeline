from aws_cdk import Stack,Duration,CustomResource, Fn
from aws_cdk import aws_iam as iam
from aws_cdk import aws_sns as sns
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_lambda as _lambda
import netdevopspipeline.accounts
from aws_cdk import custom_resources as cr
from constructs import Construct


class ValidateStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, approval_topic_arn: str, sns_topic_region: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        custom_vpcattachment_role = iam.Role(
            self,
            "customvpcattachmentresourcerole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        custom_vpcattachment_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:DescribeTransitGatewayVpcAttachments",
                    "ssm:DescribeParameters",
                    "ssm:GetParameter",
                    "ssm:GetParameterHistory",
                    "ssm:GetParameters"
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    "*"
                ],
            )
        )

        custom_analyzer_role = iam.Role(
            self,
            "customanalyzerresourcerole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        custom_analyzer_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:DescribeNetworkInsightsAnalyses"
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    "*"
                ],
            )
        )

        custom_analyzer_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sns:Publish"
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    approval_topic_arn
                ],
            )
        )
        
        custom_vpcattachment_lambda = _lambda.Function(
            self,
            "customvpcattachment",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="attachments.lambda_handler",
            role=custom_vpcattachment_role,
            timeout=Duration.seconds(60),
            code=_lambda.Code.from_asset("./netdevopspipeline/lambda_code"),
        )

        self.tgw_attachment_id = CustomResource(
            self,
            "tgwatta",
            properties={
                "HubAccount": netdevopspipeline.accounts.Dev_Hub_Primary_ENV.account,
            },
            service_token=custom_vpcattachment_lambda.function_arn,
        )

        hub_attachment_id = self.tgw_attachment_id.get_att_string("hub_attachment")
        spoke_attachment_id = self.tgw_attachment_id.get_att_string("spoke_attachment")

        cfn_network_insights_path = ec2.CfnNetworkInsightsPath(
            self, 
            "ValidationStage",
            destination=spoke_attachment_id,
            protocol="tcp",
            source=hub_attachment_id
        )

        cfn_network_insights_analysis = ec2.CfnNetworkInsightsAnalysis(
            self, 
            "RunReachabilityAnalyzer",
            network_insights_path_id=cfn_network_insights_path.attr_network_insights_path_id
        )

        network_analyzer_notification = _lambda.Function(
            self,
            "reachabilityanalyzer",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="analyzerstatus.lambda_handler",
            role=custom_analyzer_role,
            timeout=Duration.seconds(60),
            code=_lambda.Code.from_asset("./netdevopspipeline/lambda_code"),
            environment={
                "topic_region": sns_topic_region
            }
        )

        self.network_analysis = CustomResource(
            self,
            "networkanalysisstatus",
            properties={
                "networkanalysisid": cfn_network_insights_analysis.attr_network_insights_analysis_id,
                "snstopic": approval_topic_arn
            },
            service_token=network_analyzer_notification.function_arn,
        )