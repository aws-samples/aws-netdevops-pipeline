from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as _lambda
)
from aws_cdk import Aws as env
from aws_cdk import aws_iam as iam
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import CfnOutput
from constructs import Construct
from aws_cdk import aws_sns as sns


class NetDevopsFoundation(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Context variable
        organization_id = self.node.try_get_context("organization_id")
        email_endpoint = self.node.try_get_context("email_endpoint")
        pipeline_approver_sns = self.node.try_get_context("sns_topic")
        Security_findings_lambda = self.node.try_get_context("security_hub_lambda")

        attachment_lambda_role = iam.Role(
            self,
            "attachmentLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        attachment_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "securityhub:BatchImportFindings",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:securityhub:{env.REGION}:{env.ACCOUNT_ID}:product/{env.ACCOUNT_ID}/default"
                ],
            )
        )

        security_findings_lambda = _lambda.Function(
            self,
            "SecurityHubAutomation",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="securityhub.lambda_handler",
            role=attachment_lambda_role,
            timeout=Duration.seconds(180),
            code=_lambda.Code.from_asset("./netdevopsfoundations/lambda_code"),
            function_name=Security_findings_lambda,
            environment={
                "security_hub_arn": f"arn:aws:securityhub:{env.REGION}:{env.ACCOUNT_ID}:product/{env.ACCOUNT_ID}/default",
                "aws_account": env.ACCOUNT_ID
            }
        )

        source_repo = codecommit.Repository(
            self, "source_repo", repository_name="network-devops-repo"
        )

        approver_sns_topic = sns.Topic(self, "netdevops_topic", topic_name=pipeline_approver_sns)
        approver_sns_topic.add_to_resource_policy(iam.PolicyStatement(
            actions=[
                "sns:Publish"
            ],
            principals=[iam.AnyPrincipal()],
            conditions={
                "StringEquals": {
                    "aws:PrincipalOrgID": organization_id
                }
            },
            resources=[
                approver_sns_topic.topic_arn
            ]
        ))
        sns.Subscription(
            self,
            "netdevops_approver_email",
            topic=approver_sns_topic,
            endpoint=email_endpoint,
            protocol=sns.SubscriptionProtocol.EMAIL
        )

        CfnOutput(
            self,
            "approversnstopic",
            value=approver_sns_topic.topic_arn,
            export_name="pipelineapprovertopic"
        )

        CfnOutput(
            self,
            "codecommitrepo",
            value=source_repo.repository_name,
            export_name="netdevopsrepo"
        )
