from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from constructs import Construct
import netdevopspipeline.accounts


class DevHubFoundationStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.reader_role = iam.Role(
                    self,
                    "CentralTgwId-readerRole",
                    assumed_by=iam.AccountPrincipal(netdevopspipeline.accounts.Dev_Spoke_Primary_ENV.account),
                    role_name="CentralTgwId-readerRole"
                )

        self.reader_role.attach_inline_policy(iam.Policy(self, "ssm_parameter_policy",
            statements=[iam.PolicyStatement(
                actions=[
                    "ssm:DescribeParameters",
                    "ssm:GetParameter",
                    "ssm:GetParameterHistory",
                    "ssm:GetParameters"
                ],
                resources=["*"]
                )
            ]
            )
        )