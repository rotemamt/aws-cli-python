import boto3
client = boto3.client("sts")
response = client.get_caller_identity()
account_id = response["Account"]
print(account_id)