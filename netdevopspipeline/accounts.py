import aws_cdk as cdk

DEVELOPMENT_ACCOUNT_ID = "<Enter Development account ID>"
DEV_HUB_ACCOUNT_ID = "<Enter Dev Hub account ID>"
DEV_SPOKE_ACCOUNT_ID = "<Enter Dev Spoke account ID>"
PROD_HUB_ACCOUNT_ID = "<Enter Prod Hub account ID>"
PROD_SPOKE_ACCOUNT_ID = "<Enter Prod Spoke account ID>"
DEVELOPMENT_REGION = "us-east-1"
PRIMARY_REGION = "us-east-1"
DR_REGION = "us-west-2"

Development_ENV = cdk.Environment(account=DEVELOPMENT_ACCOUNT_ID, region=DEVELOPMENT_REGION)
Dev_Hub_Primary_ENV = cdk.Environment(account=DEV_HUB_ACCOUNT_ID, region=PRIMARY_REGION)
Dev_Hub_Dr_ENV = cdk.Environment(account=DEV_HUB_ACCOUNT_ID, region=DR_REGION)
Dev_Spoke_Primary_ENV = cdk.Environment(account=DEV_SPOKE_ACCOUNT_ID, region=PRIMARY_REGION)
Dev_Spoke_Dr_ENV = cdk.Environment(account=DEV_SPOKE_ACCOUNT_ID, region=DR_REGION)
Prod_Hub_Primary_ENV = cdk.Environment(account=PROD_HUB_ACCOUNT_ID, region=PRIMARY_REGION)
Prod_Hub_Dr_ENV = cdk.Environment(account=PROD_HUB_ACCOUNT_ID, region=DR_REGION)
Prod_Spoke_Primary_ENV = cdk.Environment(account=PROD_SPOKE_ACCOUNT_ID, region=PRIMARY_REGION)
Prod_Spoke_Dr_ENV = cdk.Environment(account=PROD_SPOKE_ACCOUNT_ID, region=DR_REGION)
