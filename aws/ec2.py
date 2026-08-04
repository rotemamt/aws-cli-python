import boto3
from config import CREATED_BY_TAG_KEY, CREATED_BY_TAG_VALUE, OWNER
def list_instances():
    client = boto3.client("ec2")
    response = client.describe_instances(
        Filters=[
            {"Name": f"tag:{CREATED_BY_TAG_KEY}", "Values": [CREATED_BY_TAG_VALUE]},
            {"Name": "tag:Owner", "Values": [OWNER]}
        ]
    )

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            print(instance["InstanceId"], instance["InstanceType"], instance["State"]["Name"])