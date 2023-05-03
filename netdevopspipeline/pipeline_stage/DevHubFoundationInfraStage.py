from aws_cdk import Stage
from constructs import Construct
from netdevopspipeline.pipeline_stack.DevHubFoundationInfraStack import DevHubFoundationStack


class DevHubFoundationInfraStage(Stage):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        DevHubFoundationStack(self, "DevHubFoundation")