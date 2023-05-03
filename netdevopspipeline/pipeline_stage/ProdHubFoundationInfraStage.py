from aws_cdk import Stage
from constructs import Construct
from netdevopspipeline.pipeline_stack.ProdHubFoundationInfraStack import ProdHubFoundationStack


class ProdHubFoundationInfraStage(Stage):
    def __init__(self, scope: Construct, id: str,**kwargs):
        super().__init__(scope, id, **kwargs)
        ProdHubFoundationStack(self, "ProdHubFoundation")