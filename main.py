import argparse
import sys

from aws.ec2 import create_instance, list_instances, start_instance, stop_instance
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
