import argparse, sys
from config import ALLOWED_INSTANCE_TYPES
from aws.ec2 import create_instance, list_instances, start_instance, stop_instance


parser = argparse.ArgumentParser(description="AWS self-service CLI tool")
parser.add_argument("resource", choices=["ec2", "s3", "route53"], help="Which AWS service to use")
parser.add_argument("action", choices=["list", "create", "stop", "start", "update", "upload","delete"], help="Action to perform on the resource")
parser.add_argument("--type", choices=ALLOWED_INSTANCE_TYPES, help="EC2 instance type")
parser.add_argument("--os", choices=["ubuntu", "amazon-linux"], default="ubuntu", help="Operating system")
parser.add_argument("--id", help="Instance ID")

args = parser.parse_args()


if args.resource == "ec2" and args.action in ["start", "stop"] and args.id is None:
    print("Error: --id is required for start and stop")
    sys.exit(1)

if args.resource == "ec2" and args.action == "create" and args.type is None:
    print("Error: --type is required for create")
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
