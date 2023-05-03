import aws_cdk as core
import aws_cdk.assertions as assertions
import netdevopspipeline.accounts
from aws_cdk.assertions import Match
from netdevopspipeline.netdevops_stack import NetDevopsPipelineStack

TEST_EMAIL = "test@example.com"
TEST_CONTEXT = {
    "email_endpoint": TEST_EMAIL,
}

# example tests. To run these tests, uncomment this file along with the example
# resource in netdevops/netdevops_stack.py
def test_valid_deployment_dr_region():
    app = core.App(context=TEST_CONTEXT)
    stack = NetDevopsPipelineStack(app, "netdevops", env=netdevopspipeline.accounts.Development_ENV)
    template = assertions.Template.from_stack(stack)
    template.has_resource_properties(
        "AWS::CodePipeline::Pipeline",
        {
            "Stages": Match.array_with([
                {
                    "Name": Match.any_value(),
                    "Actions": Match.array_with([
                        { 
                            "ActionTypeId": Match.object_like(
                                {
                                    "Category": "Deploy",
                                    "Owner": Match.any_value(),
                                    "Provider": Match.any_value(),
                                    "Version": Match.any_value()
                                }
                            ),
                            "Configuration": Match.any_value(),
                            "InputArtifacts": Match.any_value(),
                            "Name": Match.any_value(),
                            "Region": Match.exact("us-west-2"),
                            "RoleArn": Match.any_value(),
                            "RunOrder": Match.any_value()
                        }
                    ])
                }
            ]
            )
        }
    )


def test_valid_deployment_region():
    app = core.App(context=TEST_CONTEXT)
    stack = NetDevopsPipelineStack(app, "netdevops", env=netdevopspipeline.accounts.Development_ENV)
    template = assertions.Template.from_stack(stack)
    template.has_resource_properties(
        "AWS::CodePipeline::Pipeline",
        {
            "Stages": Match.array_with([
                {
                    "Name": Match.any_value(),
                    "Actions": Match.array_with([
                        { 
                            "ActionTypeId": Match.object_like(
                                {
                                    "Category": "Deploy",
                                    "Owner": Match.any_value(),
                                    "Provider": Match.any_value(),
                                    "Version": Match.any_value()
                                }
                            ),
                            "Configuration": Match.any_value(),
                            "InputArtifacts": Match.any_value(),
                            "Name": Match.any_value(),
                            "RoleArn": Match.any_value(),
                            "RunOrder": Match.any_value()
                        }
                    ])
                }
            ]
            )
        }
    )
