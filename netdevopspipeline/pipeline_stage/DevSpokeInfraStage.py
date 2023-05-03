from aws_cdk import Stage
from constructs import Construct
from netdevopspipeline.pipeline_stack.DevSpokeInfraStack import DevSpokeStack


class DevSpokeInfraStage(Stage):
    def __init__(self, scope: Construct, id: str, cidr: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        DevSpokeStack(self, "DevSpokeInfra", cidr=cidr)
