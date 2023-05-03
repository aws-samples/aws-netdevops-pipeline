import json
import urllib3
import logging
import boto3
import uuid
from datetime import datetime, timezone


# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
http = urllib3.PoolManager()

# boto3 client configuration 
ssm_client = boto3.client('ssm')
ec2_client = boto3.client('ec2')

def send_response(event, context, response, responseData):
    '''Send a response to CloudFormation to handle the custom resource.'''

    responseBody = {
        'Status': response,
        'Reason': f'See details in CloudWatch Log Stream: {context.log_stream_name}',
        'PhysicalResourceId': context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': responseData
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
    logger.info(f"response status is {response.status}")
    logger.info(f"the response body is {response.data}")




# Lambda handler 

def lambda_handler(event, context):
    logger.info(event)
    logger.info(context)

    hub_account = event['ResourceProperties']['HubAccount']

    if event['RequestType'] == 'Create':
        try:
            tgw_param = ssm_client.get_parameters(
                Names=['CentralTgwId']
            )
            tgw_id = tgw_param['Parameters'][0]['Value']

            F1 = [{'Name':'transit-gateway-id', 'Values': [ tgw_id ]}]
            tgw_vpc_attachment = ec2_client.describe_transit_gateway_vpc_attachments(Filters=F1)
            logger.info(tgw_vpc_attachment)
            hub_attachmentId = ""
            spoke_attachmentId = ""
            for each_attachment in tgw_vpc_attachment['TransitGatewayVpcAttachments']:
                if each_attachment['VpcOwnerId'] == hub_account:
                    hub_attachmentId = each_attachment['TransitGatewayAttachmentId']
                else:
                    spoke_attachmentId = each_attachment['TransitGatewayAttachmentId']
            data = {"hub_attachment": hub_attachmentId, "spoke_attachment": spoke_attachmentId}
            logger.info(data)
            response = "SUCCESS"
        except Exception as e:
            logger.info(f"Error getting Tgw attachmentId due to {e}")
            response = 'FAILED'
            data = {"Error": "DescribeTgwAttachment call failed"}
        send_response(event, context, response, data)

    if event['RequestType'] == 'Delete':
        response = 'SUCCESS'
        data = {"Success": "Deletion operation nothing to do...."}
        send_response(event, context, response, data)




    




