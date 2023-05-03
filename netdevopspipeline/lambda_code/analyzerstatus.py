import json
import urllib3
import logging
import boto3
import time
import os

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
http = urllib3.PoolManager()

# Env variable
sns_topic_region = os.environ["topic_region"]

# boto3 client configuration 
ec2_client = boto3.client('ec2')
sns_client = boto3.client('sns', region_name=sns_topic_region)

def send_response(event, context, response):
    '''Send a response to CloudFormation to handle the custom resource.'''

    responseBody = {
        'Status': response,
        'Reason': f'See details in CloudWatch Log Stream: {context.log_stream_name}',
        'PhysicalResourceId': context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId']
    }

    logger.info('RESPONSE BODY: \n' + json.dumps(responseBody))

    responseUrl = event['ResponseURL']
    json_responseBody = json.dumps(responseBody)
    headers = {
        'content-type': '',
        'content-length': str(len(json_responseBody))
    }

    response = http.request('PUT', responseUrl, headers=headers, 
                            body=json_responseBody)


# Lambda handler 

def lambda_handler(event, context):
    logger.info(event)
    logger.info(context)

    network_analysis_id = event['ResourceProperties']['networkanalysisid']
    sns_topic_arn = event['ResourceProperties']['snstopic']

    if (event['RequestType'] == 'Create') or (event['RequestType'] == 'Update'):
        try:
            time.sleep(30)
            describe_analysis_status = ec2_client.describe_network_insights_analyses(NetworkInsightsAnalysisIds=[network_analysis_id])
            analysis_status = describe_analysis_status["NetworkInsightsAnalyses"][0]["NetworkPathFound"]
            if analysis_status:
                sns_client.publish(
                    TopicArn=sns_topic_arn,
                    Message=f"The Reachabilty analyzer Status between Hub and Spoke VPC Successful, to review the path check the analysis Id {network_analysis_id}. Approve the pipeline to deploy to Production"
                )
                response = "SUCCESS"
            else:
                sns_client.publish(
                    TopicArn=sns_topic_arn,
                    Message=f"The Reachabilty analyzer Status between Hub and Spoke VPC Failed, to review the path check the analysis Id {network_analysis_id}."
                )
                response = "SUCCESS"
        except Exception as e:
            logger.info(f"Error getting the status of Reachabilty analyzer due to {e}")
            response = 'FAILED'
        send_response(event, context, response)

    if event['RequestType'] == 'Delete':
        response = 'SUCCESS'
        send_response(event, context, response)
