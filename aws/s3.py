import boto3
import os
import json
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


def list_buckets():
    client = boto3.client("s3")
    response = client.list_buckets()

    count = 0
    for bucket in response["Buckets"]:
        name = bucket["Name"]

        try:
            tag_response = client.get_bucket_tagging(Bucket=name)
            tags = tag_response["TagSet"]
        except client.exceptions.ClientError:
            tags = []

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
            print(name)
            count += 1

    if count == 0:
        print("No buckets found.")


def create_bucket(name, public):
    if public:
        answer = input("Make this bucket PUBLIC? Type yes to confirm: ")
        if answer not in ["yes", "Yes", "Y", "y"]:
            print("Aborted")
            return

    client = boto3.client("s3")
    try:
        client.create_bucket(Bucket=name)
    except client.exceptions.ClientError as e:
        print(f"Error creating bucket: {e}")
        return

    tags = [
        {"Key": CREATED_BY_TAG_KEY, "Value": CREATED_BY_TAG_VALUE},
        {"Key": OWNER_TAG_KEY, "Value": OWNER_TAG_VALUE},
        {"Key": PROJECT_TAG_KEY, "Value": PROJECT_TAG_VALUE},
        {"Key": ENVIRONMENT_TAG_KEY, "Value": ENVIRONMENT_TAG_VALUE},
    ]

    client.put_bucket_tagging(Bucket=name, Tagging={"TagSet": tags})
    if public:
        client.put_public_access_block(
            Bucket=name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": False,
                "IgnorePublicAcls": False,
                "BlockPublicPolicy": False,
                "RestrictPublicBuckets": False,
            },
        )
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{name}/*",
                }
            ],
        }
        client.put_bucket_policy(Bucket=name, Policy=json.dumps(policy))
    print(f"Created bucket {name}")


def upload_file(bucket_name, file_path):
    if not os.path.exists(file_path):
        print(f"Error: file not found: {file_path}")
        return

    client = boto3.client("s3")
    try:
        tag_response = client.get_bucket_tagging(Bucket=bucket_name)
        tags = tag_response["TagSet"]
    except client.exceptions.ClientError:
        tags = []

    has_created_by = False
    has_owner = False

    for tag in tags:
        if tag["Key"] == CREATED_BY_TAG_KEY and tag["Value"] == CREATED_BY_TAG_VALUE:
            has_created_by = True
        if tag["Key"] == OWNER_TAG_KEY and tag["Value"] == OWNER_TAG_VALUE:
            has_owner = True

    if not has_created_by or not has_owner:
        print(f"Error: {bucket_name} was not created by this CLI.")
        return

    key = os.path.basename(file_path)
    client.upload_file(file_path, bucket_name, key)
    print(f"Uploaded {key} to {bucket_name}")
