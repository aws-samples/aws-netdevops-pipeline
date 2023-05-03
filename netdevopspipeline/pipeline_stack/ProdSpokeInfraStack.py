from aws_cdk import Stack,Aws
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
import netdevopspipeline.accounts
import uuid
from aws_cdk import custom_resources as cr
from aws_cdk import CfnTag
from constructs import Construct


class ProdSpokeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, cidr: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.tgw_param_reader = cr.AwsCustomResource(
            self,
            "tgwidreader",
            policy=cr.AwsCustomResourcePolicy.from_statements(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["sts:AssumeRole"],
                        resources=[
                            f"arn:{Aws.PARTITION}:iam::{netdevopspipeline.accounts.Prod_Hub_Primary_ENV.account}:role/CentralTgwId-readerRole"
                        ],
                    )
                ]
            ),
            on_create=cr.AwsSdkCall(
                action="getParameter",
                service="SSM",
                parameters={"Name": "CentralTgwId"},
                assumed_role_arn=f"arn:{Aws.PARTITION}:iam::{netdevopspipeline.accounts.Prod_Hub_Primary_ENV.account}:role/CentralTgwId-readerRole",
                physical_resource_id=cr.PhysicalResourceId.of(
                    id=str(uuid.uuid4()).split("-")[0]
                ),
            ),
            on_update=cr.AwsSdkCall(
                action="getParameter",
                service="SSM",
                parameters={"Name": "CentralTgwId"},
                assumed_role_arn=f"arn:{Aws.PARTITION}:iam::{netdevopspipeline.accounts.Prod_Hub_Primary_ENV.account}:role/CentralTgwId-readerRole",
                physical_resource_id=cr.PhysicalResourceId.of(
                    id=str(uuid.uuid4()).split("-")[0]
                ),
            ),
        )
        tgw_id = self.tgw_param_reader.get_response_field("Parameter.Value")

        self.vpc = ec2.Vpc(
            self,
            "spoke_vpc",
            max_azs=2,
            cidr=cidr,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    name="private",
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    name="tgw",
                    cidr_mask=28,
                ),
            ],
            nat_gateways=0,
        )

        private_subnets = list(self.vpc.isolated_subnets[:2])
        tgw_subnets = list(self.vpc.isolated_subnets[-2:])

        private_subnets_ids = [subnet.subnet_id for subnet in private_subnets]
        tgw_subnets_ids = [subnet.subnet_id for subnet in tgw_subnets]

        tgw_attachment = ec2.CfnTransitGatewayAttachment(
            self,
            "spoke_tgw_attachment",
            subnet_ids=tgw_subnets_ids,
            transit_gateway_id=tgw_id,
            vpc_id=self.vpc.vpc_id,
            tags=[CfnTag(key="Name", value="spoke_account_attachment")],
        )

        # Route table with route to TGW
        route_table_private_subnets = ec2.CfnRouteTable(
            self,
            "route_table_private_subnets",
            vpc_id=self.vpc.vpc_id,
            tags=[CfnTag(key="Name", value="private_subnet_rt")],
        )

        # Route table for TGW subnets
        route_table_tgw_attachment_subnets = ec2.CfnRouteTable(
            self,
            "route_table_tgw_attachment_subnets",
            vpc_id=self.vpc.vpc_id,
            tags=[CfnTag(key="Name", value="tgw_attachment_subnet_rt")],
        )

        # Route with destination 0.0.0.0/0 to TGW
        route = ec2.CfnRoute(
            self,
            "route_to_tgw",
            route_table_id=route_table_private_subnets.attr_route_table_id,
            destination_cidr_block="0.0.0.0/0",
            transit_gateway_id=tgw_id,
        )
        route.node.add_dependency(tgw_attachment)

        # Remove default Route Tables and associations from the subnets
        for subnet in tgw_subnets:
            subnet.node.try_remove_child("RouteTableAssociation")
            subnet.node.try_remove_child("RouteTable")

        for subnet in private_subnets:
            subnet.node.try_remove_child("RouteTableAssociation")
            subnet.node.try_remove_child("RouteTable")

        # Create route table association for private subnets
        for count, subnet_id in enumerate(private_subnets_ids):
            private_association = ec2.CfnSubnetRouteTableAssociation(
                self,
                f"private_subnet_rt_association_{count}",
                route_table_id=route_table_private_subnets.attr_route_table_id,
                subnet_id=subnet_id,
            )
            private_association.node.add_dependency(self.vpc)

        # Create route table association for tgw attachment subnets
        for count, subnet_id in enumerate(tgw_subnets_ids):
            tgw_association = ec2.CfnSubnetRouteTableAssociation(
                self,
                f"tgw_attachment_subnet_rt_association_{count}",
                route_table_id=route_table_tgw_attachment_subnets.attr_route_table_id,
                subnet_id=subnet_id,
            )
            tgw_association.node.add_dependency(self.vpc)
