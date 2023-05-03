from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ssm as ssm
from aws_cdk import aws_ram as ram
from aws_cdk import aws_iam as iam
from aws_cdk import CfnTag
from constructs import Construct
import netdevopspipeline.accounts

class DevHubStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, cidr: str, dr_cidr: str, region: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.transit_gateway = ec2.CfnTransitGateway(
            self,
            "AWSTransitGateway",
            amazon_side_asn=65533,
            auto_accept_shared_attachments="enable",
            default_route_table_association="enable",
            default_route_table_propagation="enable",
            description="AWSTransitGateway",
            dns_support="enable",
            multicast_support="disable",
            tags=[CfnTag(key="Name", value="AWSTransitGateway")],
            transit_gateway_cidr_blocks=["10.100.10.0/24"],
            vpn_ecmp_support="enable",
        )

        ram_share = ram.CfnResourceShare(
            self,
            "tgwshare",
            allow_external_principals=True,
            resource_arns=[f"arn:aws:ec2:{region}:{netdevopspipeline.accounts.Dev_Hub_Primary_ENV.account}:transit-gateway/{self.transit_gateway.attr_id}"],
            principals=[f"{netdevopspipeline.accounts.Dev_Spoke_Primary_ENV.account}"],
            name="tgw-share",
        )

        self.ssm_store = ssm.StringParameter(
            self,
            "tgwssm",
            parameter_name="CentralTgwId",
            string_value=self.transit_gateway.attr_id
        )

        self.vpc = ec2.Vpc(
            self,
            "ProdVpc",
            max_azs=2,
            cidr=cidr,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    name="Private",
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC,
                    name="Public",
                    cidr_mask=24,
                    map_public_ip_on_launch=True
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    name="tgw",
                    cidr_mask=28,
                )
            ],
        )

        self.private_subnets = list(self.vpc.isolated_subnets[:2])
        self.private_egress_subnet = list(self.vpc.private_subnets[:2])
        self.private_subnets_ids = [subnet.subnet_id for subnet in self.private_subnets]
        self.public_subnets = list(self.vpc.public_subnets)

        for subnet in self.public_subnets:
            cfnsubnet = subnet.node.default_child
            cfnsubnet.cfn_options.metadata = {
                "cfn_nag": {
                    "rules_to_suppress": [
                        {"id": "W33"}
                    ]
                }
            }


        for subnet in self.private_subnets:
            subnet.node.try_remove_child("RouteTableAssociation")
            subnet.node.try_remove_child("RouteTable")

        self.tgw_attachment = ec2.CfnTransitGatewayAttachment(
            self,
            "tgw-attachment",
            subnet_ids=self.private_subnets_ids,
            transit_gateway_id=self.transit_gateway.attr_id,
            vpc_id=self.vpc.vpc_id,
            tags=[CfnTag(key="Name", value="Hub-Account-Attachment")],
        )

        self.route_table_tgw = ec2.CfnRouteTable(
            self,
            "RouteTableTGW",
            vpc_id=self.vpc.vpc_id,
            tags=[CfnTag(key="Name", value="TGW-RouteTable")],
        )
        
        self.tgw_route = ec2.CfnRoute(
            self,
            "RouteToTGW",
            route_table_id=self.route_table_tgw.attr_route_table_id,
            destination_cidr_block="0.0.0.0/0",
            transit_gateway_id=self.transit_gateway.attr_id,
        )
        self.tgw_route.node.add_dependency(self.tgw_attachment)
        count = 1
        for egress_subnet in self.private_egress_subnet:
            self.private_egress_route = ec2.CfnRoute(
                self,
                f"EgressRoute-{count}",
                route_table_id=egress_subnet.route_table.route_table_id,
                destination_cidr_block=dr_cidr,
                transit_gateway_id=self.transit_gateway.attr_id,
            )
            self.private_egress_route.node.add_dependency(self.tgw_attachment)
            count = count + 1

        for count, subnet_id in enumerate(self.private_subnets_ids, start=1):
            self.route_association = ec2.CfnSubnetRouteTableAssociation(
                self,
                f"RTAssociation-{count}",
                route_table_id=self.route_table_tgw.attr_route_table_id,
                subnet_id=subnet_id,
            )
        