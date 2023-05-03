import os 
import logging
import boto3
import uuid
from datetime import datetime, timezone


# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment Variable 
security_hub_arn = os.getenv("security_hub_arn")
account = os.getenv("aws_account")

# boto3 client configuration 
securityhub = boto3.client('securityhub')


# Lambda handler 

def lambda_handler(event, context):
    logger.info(event)
    logger.info(context)
    
    title=event["messageType"]
    reportType = event["reportType"]
    findings = event["report"]
    
    new_findings = []
    try:
        for each_finding in findings:
            new_findings.append({
                'SchemaVersion': '2018-10-08',
                'Id': str(uuid.uuid4()),
                'ProductArn': security_hub_arn,
                'GeneratorId': reportType,
                'CreatedAt': datetime.now(tz=timezone.utc).isoformat(),
                'UpdatedAt': datetime.now(tz=timezone.utc).isoformat(),
                'AwsAccountId': account,
                'Types': ['Infrastructure Configuration Checks'],
                'Description': each_finding["file_results"]["violations"][0]["message"],
                'ProductName': 'CFN Nag Automation',
                'CompanyName': 'cfn-nag',
                'Severity': {
                    'Normalized': 100
                },
                'Confidence': 100,
                'Criticality': 100,
                'Title': title,
                'Resources': [
                    {
                        "Id" : "W33",
                        "Type": "Other"
                    }
                ],
                'Vulnerabilities': [
                    {
                        "Id": "W33",
                        "RelatedVulnerabilities": each_finding["file_results"]["violations"][0]["logical_resource_ids"],
                        "VulnerablePackages": [
                            {
                                "FilePath": each_finding["filename"],
                                "Name":  each_finding["file_results"]["violations"][0]["name"]
                            }]
                    }
                ],
                'WorkflowState': 'NEW',
                'Compliance': {'Status': 'FAILED'},
                'RecordState': 'ACTIVE'   
            })
        securityhub.batch_import_findings(Findings=new_findings)
    except Exception as e:
        logger.error(f"The findings to security hub failed due to {e}")
        raise e
