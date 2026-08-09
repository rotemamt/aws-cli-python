import boto3

from config import (
    ALLOWED_INSTANCE_TYPES,
    AMAZON_LINUX_AMI_PARAMETER,
    CREATED_BY_TAG_KEY,
    CREATED_BY_TAG_VALUE,
    ENVIRONMENT_TAG_KEY,
    ENVIRONMENT_TAG_VALUE,
    MAX_RUNNING_INSTANCES,
    OWNER_TAG_KEY,
    OWNER_TAG_VALUE,
    PROJECT_TAG_KEY,
    PROJECT_TAG_VALUE,
    UBUNTU_AMI_PARAMETER,
)


def list_instances():
    client = boto3.client("ec2")
    response = client.describe_instances(
        Filters=[
            {"Name": f"tag:{CREATED_BY_TAG_KEY}", "Values": [CREATED_BY_TAG_VALUE]},
            {"Name": f"tag:{OWNER_TAG_KEY}", "Values": [OWNER_TAG_VALUE]},
        ]
    )
    count = 0
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            print(
                instance["InstanceId"],
                instance["InstanceType"],
                instance["State"]["Name"],
            )
            count += 1

    if count == 0:
        print("No instances found.")


def count_running_instances():
    client = boto3.client("ec2")
    response = client.describe_instances(
        Filters=[
            {"Name": f"tag:{CREATED_BY_TAG_KEY}", "Values": [CREATED_BY_TAG_VALUE]},
            {"Name": f"tag:{OWNER_TAG_KEY}", "Values": [OWNER_TAG_VALUE]},
            {"Name": "instance-state-name", "Values": ["running", "pending"]},
        ]
    )
    count = 0
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            count += 1
    return count


def get_latest_ami(os_name):
    if os_name == "ubuntu":
        parameter_name = UBUNTU_AMI_PARAMETER
    else:
        parameter_name = AMAZON_LINUX_AMI_PARAMETER

    client = boto3.client("ssm")
    response = client.get_parameter(Name=parameter_name)
    return response["Parameter"]["Value"]


def create_instance(instance_type, os_name):
    if instance_type not in ALLOWED_INSTANCE_TYPES:
        print(f"Error: {instance_type} not allowed.")
        return
    current = count_running_instances()
    if current >= MAX_RUNNING_INSTANCES:
        print(
            f"Error: {MAX_RUNNING_INSTANCES} are already running, you've hit the limit."
        )
        return

    ami_id = get_latest_ami(os_name)
    client = boto3.client("ec2")
    response = client.run_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": CREATED_BY_TAG_KEY, "Value": CREATED_BY_TAG_VALUE},
                    {"Key": OWNER_TAG_KEY, "Value": OWNER_TAG_VALUE},
                    {"Key": PROJECT_TAG_KEY, "Value": PROJECT_TAG_VALUE},
                    {"Key": ENVIRONMENT_TAG_KEY, "Value": ENVIRONMENT_TAG_VALUE},
                ],
            }
        ],
    )
    instance_id = response["Instances"][0]["InstanceId"]
    print(f"Instance Id: {instance_id}, Instance type: {instance_type}, AMI: {ami_id}")


def stop_instance(instance_id):
    client = boto3.client("ec2")
    try:
        response = client.describe_instances(InstanceIds=[instance_id])
    except client.exceptions.ClientError as e:
        print(f"Error: {e}")
        return

    instance = response["Reservations"][0]["Instances"][0]
    tags = instance.get("Tags", [])

    has_created_by = False
    has_owner = False

    for tag in tags:
        if tag["Key"] == CREATED_BY_TAG_KEY and tag["Value"] == CREATED_BY_TAG_VALUE:
            has_created_by = True
        if tag["Key"] == OWNER_TAG_KEY and tag["Value"] == OWNER_TAG_VALUE:
            has_owner = True

    if not has_created_by or not has_owner:
        print(f"Error: {instance_id} was not created by this CLI. Refusing to stop it.")
        return

    state = instance["State"]["Name"]
    if state in ["stopped", "stopping"]:
        print(f"{instance_id} is already {state}.")
        return
    if state in ["terminated", "shutting-down"]:
        print(f"{instance_id} is already {state}.")
        return

    client.stop_instances(InstanceIds=[instance_id])
    print(f"Stopping {instance_id}")


def start_instance(instance_id):
    client = boto3.client("ec2")
    try:
        response = client.describe_instances(InstanceIds=[instance_id])
    except client.exceptions.ClientError as e:
        print(f"Error: {e}")
        return

    instance = response["Reservations"][0]["Instances"][0]
    tags = instance.get("Tags", [])

    has_created_by = False
    has_owner = False

    for tag in tags:
        if tag["Key"] == CREATED_BY_TAG_KEY and tag["Value"] == CREATED_BY_TAG_VALUE:
            has_created_by = True
        if tag["Key"] == OWNER_TAG_KEY and tag["Value"] == OWNER_TAG_VALUE:
            has_owner = True

    if not has_created_by or not has_owner:
        print(
            f"Error: {instance_id} was not created by this CLI. Refusing to start it."
        )
        return

    state = instance["State"]["Name"]
    if state != "stopped":
        print(f"Cannot start {instance_id}. Instance is already {state}.")
        return

    client.start_instances(InstanceIds=[instance_id])
    print(f"Starting {instance_id}")
