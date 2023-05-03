import aws_cdk as cdk
from netdevopspipeline.netdevops_stack import NetDevopsPipelineStack
import netdevopspipeline.accounts
from netdevopsfoundations.infra_prereq_stack import NetDevopsFoundation

app = cdk.App()

stack_type = app.node.try_get_context("infra_type")

if stack_type == "NetDevopsFoundation":
    NetDevopsFoundation(app, "NetDevopsFoundation", env=netdevopspipeline.accounts.Development_ENV)
else:
    NetDevopsPipelineStack(app, "NetdevopsPipelineStack", env=netdevopspipeline.accounts.Development_ENV)

app.synth()
