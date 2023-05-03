from aws_cdk import Stage
from constructs import Construct
from netdevopspipeline.pipeline_stack.ProdSpokeInfraStack import ProdSpokeStack


class ProdSpokeInfraStage(Stage):
    def __init__(self, scope: Construct, id: str, cidr: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        ProdSpokeStack(self, "ProdSpokeInfra", cidr=cidr)