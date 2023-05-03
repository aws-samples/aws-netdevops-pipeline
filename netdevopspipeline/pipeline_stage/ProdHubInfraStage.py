from aws_cdk import Stage
from constructs import Construct
from netdevopspipeline.pipeline_stack.ProdHubInfraStack import ProdHubStack


class ProdHubInfraStage(Stage):
    def __init__(self, scope: Construct, id: str, cidr: str, dr_cidr:str, region: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        ProdHubStack(self, "ProdHubInfra", cidr=cidr, dr_cidr=dr_cidr, region=region)