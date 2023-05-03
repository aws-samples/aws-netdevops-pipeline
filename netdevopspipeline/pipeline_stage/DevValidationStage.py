from aws_cdk import Stage
from constructs import Construct
from netdevopspipeline.pipeline_stack.DevValidateStack import ValidateStack


class ValidationStage(Stage):
    def __init__(self, scope: Construct, id: str, topic_arn:str, Dev_account_region:str, **kwargs):
        super().__init__(scope, id, **kwargs)
        ValidateStack(self, "ValidateReachability", approval_topic_arn=topic_arn, sns_topic_region=Dev_account_region)