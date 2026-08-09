import time

import boto3

from config import (
    CREATED_BY_TAG_KEY,
    CREATED_BY_TAG_VALUE,
    ENVIRONMENT_TAG_KEY,
    ENVIRONMENT_TAG_VALUE,
    OWNER_TAG_KEY,
    OWNER_TAG_VALUE,
    PROJECT_TAG_KEY,
    PROJECT_TAG_VALUE,
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

    has_created_by = False
    has_owner = False

    for tag in tags:
        if tag["Key"] == CREATED_BY_TAG_KEY and tag["Value"] == CREATED_BY_TAG_VALUE:
            has_created_by = True
        if tag["Key"] == OWNER_TAG_KEY and tag["Value"] == OWNER_TAG_VALUE:
            has_owner = True

    if not has_created_by or not has_owner:
        print(f"Error: zone {zone_id} was not created by this CLI.")
        return

    client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": action,
                    "ResourceRecordSet": {
                        "Name": record_name,
                        "Type": "A",
                        "TTL": 300,
                        "ResourceRecords": [{"Value": record_value}],
                    },
                }
            ]
        },
    )
    print(f"{action} {record_name} -> {record_value}")
    

def list_records(zone_id):
    client = boto3.client("route53")
    tag_response = client.list_tags_for_resource(
        ResourceType="hostedzone", ResourceId=zone_id
    )
    tags = tag_response["ResourceTagSet"]["Tags"]

    has_created_by = False
    has_owner = False

    for tag in tags:
        if tag["Key"] == CREATED_BY_TAG_KEY and tag["Value"] == CREATED_BY_TAG_VALUE:
            has_created_by = True
        if tag["Key"] == OWNER_TAG_KEY and tag["Value"] == OWNER_TAG_VALUE:
            has_owner = True

    if not has_created_by or not has_owner:
        print(f"Error: zone {zone_id} was not created by this CLI.")
        return
    
    response = client.list_resource_record_sets(HostedZoneId=zone_id)
    
    count = 0
    for record in response["ResourceRecordSets"]:
        if record["Type"] != "A":
            continue
        value = record["ResourceRecords"][0]["Value"]
        print(record["Name"], record["Type"], value)
        count += 1
        
    if count == 0:
        print("No records found.")
        
    
def delete_zone(zone_id):
    client = boto3.client("route53")
    tag_response = client.list_tags_for_resource(
        ResourceType="hostedzone", ResourceId=zone_id
    )
    tags = tag_response["ResourceTagSet"]["Tags"]

    has_created_by = False
    has_owner = False

    for tag in tags:
        if tag["Key"] == CREATED_BY_TAG_KEY and tag["Value"] == CREATED_BY_TAG_VALUE:
            has_created_by = True
        if tag["Key"] == OWNER_TAG_KEY and tag["Value"] == OWNER_TAG_VALUE:
            has_owner = True

    if not has_created_by or not has_owner:
        print(f"Error: zone {zone_id} was not created by this CLI.")
        return
    

    answer = input("Are you sure u want to delete? Type yes to confirm: ")
    if answer not in ["yes", "Yes", "Y", "y"]:
        print("Aborted")
        return
    
    try:
        client.delete_hosted_zone(Id=zone_id)
    except client.exceptions.ClientError as e:
        print(f"Error deleting zone: {e}")
        return

    print(f"{zone_id} was deleted")
