import argparse
parser = argparse.ArgumentParser(description="AWS self-service CLI tool")
parser.add_argument("resource", choices=["ec2", "s3", "route53"], help="Which AWS service to use")
parser.add_argument("action", choices=["list", "create", "stop", "start", "update", "upload","delete"], help="Action to perform on the resource")
args = parser.parse_args()
print(f"Resource: {args.resource}, Action: {args.action}")
