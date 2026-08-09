import argparse
import sys

from aws.ec2 import create_instance, list_instances, start_instance, stop_instance
from aws.route53 import (
    change_record,
    create_zone,
    delete_zone,
    list_records,
    list_zones,
)
from aws.s3 import create_bucket, list_buckets, upload_file
from config import ALLOWED_INSTANCE_TYPES

parser = argparse.ArgumentParser(description="AWS self-service CLI tool")
parser.add_argument(
    "resource", choices=["ec2", "s3", "route53"], help="Which AWS service to use"
)
parser.add_argument(
    "action",
    choices=["list", "create", "stop", "start", "update", "upload", "delete"],
    help="Action to perform on the resource",
)
parser.add_argument("--type", choices=ALLOWED_INSTANCE_TYPES, help="EC2 instance type")
parser.add_argument(
    "--os",
    choices=["ubuntu", "amazon-linux"],
    default="ubuntu",
    help="Operating system",
)
parser.add_argument("--id", help="Instance ID")
parser.add_argument("--name", help="The Bucket name")
parser.add_argument("--file", help="Path to the file to upload")
parser.add_argument("--public", action="store_true", help="Make the S3 Bucket public")
parser.add_argument("--zone-id", help="Route53 hostez zone ID")
parser.add_argument("--record-name", help="DNS record name, e.g www.example.com")
parser.add_argument("--record-value", help="DNS record value, e.g an IPv4 address")


args = parser.parse_args()


if args.resource == "ec2" and args.action in ["start", "stop"] and args.id is None:
    print("Error: --id is required for start and stop")
    sys.exit(1)

if args.resource == "ec2" and args.action == "create" and args.type is None:
    print("Error: --type is required for create")
    sys.exit(1)

if args.resource == "s3" and args.action in ["create", "upload"] and args.name is None:
    print("Error: --name is required for create and upload")
    sys.exit(1)

if args.resource == "s3" and args.action == "upload" and args.file is None:
    print("Error: --file is required for upload")
    sys.exit(1)

if args.resource == "route53" and args.action in ["create", "update", "delete"] and args.record_name and args.zone_id is None:
    print("Error: --zone-id is required for record operations")
    sys.exit(1)

if args.resource == "route53" and args.action in ["create", "update", "delete"] and args.record_name and args.record_value is None:
    print("Error: --record-value is required for record operations")
    sys.exit(1)

if args.resource == "route53" and args.action == "create" and args.record_name is None and args.name is None:
    print("Error: --name is required to create a zone")
    sys.exit(1)

if args.resource == "route53" and args.action == "delete" and args.record_name is None and args.zone_id is None:
    print("Error: --zone-id is required to delete a zone")
    sys.exit(1)


if args.resource == "ec2":
    if args.action == "list":
        list_instances()
    elif args.action == "create":
        create_instance(args.type, args.os)
    elif args.action == "start":
        start_instance(args.id)
    elif args.action == "stop":
        stop_instance(args.id)
    else:
        print(f"Action '{args.action}' is not supported for ec2.")

elif args.resource == "s3":
    if args.action == "list":
        list_buckets()
    elif args.action == "create":
        create_bucket(args.name, args.public)
    elif args.action == "upload":
        upload_file(args.name, args.file)
    else:
        print(f"Action '{args.action}' is not supported for s3.")

elif args.resource == "route53":
    if args.action == "list":
        if args.zone_id:
            list_records(args.zone_id)
        else:
            list_zones()
    elif args.action == "create":
        if args.record_name:
            change_record(args.zone_id, args.record_name, args.record_value, "UPSERT")
        else:
            create_zone(args.name)
    elif args.action == "update":
        change_record(args.zone_id, args.record_name, args.record_value, "UPSERT")
    elif args.action == "delete":
        if args.record_name:
            change_record(args.zone_id, args.record_name, args.record_value, "DELETE")
        else:
            delete_zone(args.zone_id)
    else:
        print(f"Action '{args.action}' is not supported for route53.")