import boto3
import time
from config import (
    CREATED_BY_TAG_KEY,
    CREATED_BY_TAG_VALUE,
    OWNER_TAG_KEY,
    OWNER_TAG_VALUE,
    PROJECT_TAG_KEY,
    PROJECT_TAG_VALUE,
    ENVIRONMENT_TAG_KEY,
    ENVIRONMENT_TAG_VALUE,
)


def list_zones():
    client = boto3.client("route53")
    response = client.list_hosted_zones()

    count = 0
    for zone in response["HostedZones"]:
        zone_id = zone["Id"].split("/")[-1]
        tag_response = client.list_tags_for_resource(
            ResourceType="hostedzone", ResourceId=zone_id
        )
        tags = tag_response["ResourceTagSet"]["Tags"]

        has_created_by = False
        has_owner = False

        for tag in tags:
            if (
                tag["Key"] == CREATED_BY_TAG_KEY
                and tag["Value"] == CREATED_BY_TAG_VALUE
            ):
                has_created_by = True
            if tag["Key"] == OWNER_TAG_KEY and tag["Value"] == OWNER_TAG_VALUE:
                has_owner = True

        if has_created_by and has_owner:
            print(zone["Name"], zone_id)
            count += 1

    if count == 0:
        print("No zones found.")


def create_zone(domain_name):
    client = boto3.client("route53")
    response = client.create_hosted_zone(
        Name=domain_name, CallerReference=str(time.time())
    )
    zone_id = response["HostedZone"]["Id"].split("/")[-1]
    tags = [
        {"Key": CREATED_BY_TAG_KEY, "Value": CREATED_BY_TAG_VALUE},
        {"Key": OWNER_TAG_KEY, "Value": OWNER_TAG_VALUE},
        {"Key": PROJECT_TAG_KEY, "Value": PROJECT_TAG_VALUE},
        {"Key": ENVIRONMENT_TAG_KEY, "Value": ENVIRONMENT_TAG_VALUE},
    ]
    client.change_tags_for_resource(
        ResourceType="hostedzone", ResourceId=zone_id, AddTags=tags
    )
    print(f"'{domain_name}' created. zone id: '{zone_id}'")


def change_record(zone_id, record_name, record_value, action):
    client = boto3.client("route53")
    tag_response = client.list_tags_for_resource(
        ResourceType="hostedzone", ResourceId=zone_id
    )
    tags = tag_response["ResourceTagSet"]["Tags"]
