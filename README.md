# platform-cli

A self-service command line tool that lets developers create and manage AWS
resources on their own, without giving them the AWS console and without waiting for a DevOps engineer to do it for them.

The point is not to wrap the AWS CLI. The point is the guardrails: this tool only allows cheap instance types, caps how many machines you can run, asks before it exposes a bucket to the internet, and refuses to touch anything the user who uses this tool did not create.

Supported services:

| Service | Actions |
| --- | --- |
| EC2 | create, list, start, stop |
| S3 | create, upload, list |
| Route53 | create zone, delete zone, create/update/delete records, list |

## Prerequisites

- Python 3.10 or newer (developed on 3.14)
- An AWS account and the AWS CLI installed
- AWS credentials configured locally:

  ```bash
  aws configure
  ```

  The tool never stores credentials. `boto3` picks them up from the standard credential chain: environment variables, then `~/.aws/credentials`, then an IAM role. 
  Nothing sensitive lives in this repository.

- The IAM user or role you use needs permissions for:
  - EC2: `RunInstances`, `DescribeInstances`, `StartInstances`, `StopInstances`, `CreateTags`
  - S3: `CreateBucket`, `ListAllMyBuckets`, `PutObject`, `GetBucketTagging`, `PutBucketTagging`, `PutBucketPolicy`, `PutPublicAccessBlock`
  - Route53: `CreateHostedZone`, `DeleteHostedZone`, `ListHostedZones`, `ChangeResourceRecordSets`, `ListResourceRecordSets`, `ChangeTagsForResource`, `ListTagsForResource`
  - SSM: `GetParameter` (used to look up the latest AMI)

## Installation

```bash
git clone https://github.com/rotemamt/aws-cli-python.git
cd aws-cli-python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Check that your credentials work before doing anything else:

```bash
python check_aws_connectivity.py
```

It should prints your AWS account ID. If it errors, fix `aws configure` first.

## Configuration

All policy lives in `config.py`— allowed instance types, the running-instance cap, the tag names and values, and the SSM parameter paths for AMI lookup.

Before using the tool, set `OWNER_TAG_VALUE` in `config.py` to your own name.
This is what separates your resources from everyone else's in a shared account.

## Usage

Every command has the same shape:

```bash
python main.py <resource> <action> [options]
```

Full option list:

```bash
python main.py --help
```

### EC2

```bash
# create an instance (only t3.micro or t2.small are allowed)

`--os` defaults to `ubuntu` if you don't specify.

python main.py ec2 create --type t3.micro --os ubuntu
python main.py ec2 create --type t2.small --os amazon-linux

# list only the instances this CLI created
python main.py ec2 list

# stop and start (only works on instances this CLI created)
python main.py ec2 stop --id i-0123456789abcdef0
python main.py ec2 start --id i-0123456789abcdef0
```

### S3

```bash
# private bucket (the default, and the safe one)
python main.py s3 create --name my-unique-bucket-name

# public bucket - prompts for confirmation before doing anything
python main.py s3 create --name my-unique-bucket-name --public

# upload a file (only into buckets this CLI created)
python main.py s3 upload --name my-unique-bucket-name --file ./notes.txt

# list only the buckets this CLI created
python main.py s3 list
```

Bucket names are globally unique across all of AWS, so pick something specific.

### Route53

```bash
# create a hosted zone
python main.py route53 create --name example.com

# list your zones
python main.py route53 list

# list the records in one zone
python main.py route53 list --zone-id Z0123456789ABCDEFGHIJ

# create or update a record (both use UPSERT)
python main.py route53 create --zone-id Z0123456789ABCDEFGHIJ \
  --record-name www.example.com --record-value 1.2.3.4

python main.py route53 update --zone-id Z0123456789ABCDEFGHIJ \
  --record-name www.example.com --record-value 5.6.7.8

# delete a record- the value must match what is currently stored
python main.py route53 delete --zone-id Z0123456789ABCDEFGHIJ \
  --record-name www.example.com --record-value 5.6.7.8

# delete a zone (asks for confirmation, and only works if the zone is empty)
python main.py route53 delete --zone-id Z0123456789ABCDEFGHIJ
```

Tip: Hosted zones cost $0.50 per month each. Delete them when you are done.

## Guardrails

| Rule | Where it is enforced | What happens |
| --- | --- | --- |
| Only `t3.micro` or `t2.small` | argparse `choices` and `create_instance` | rejected before any AWS call |
| Maximum 2 running instances | `count_running_instances` in `aws/ec2.py` | counts tagged instances in `running` or `pending`, refuses at the limit |
| Public buckets need confirmation | `create_bucket` in `aws/s3.py` | typed confirmation required, anything else aborts |
| Only touch resources this CLI created | every start/stop/upload/record function | tags are checked before the action, refused if they do not match |
| Zone deletion is irreversible | `delete_zone` in `aws/route53.py` | typed confirmation required |
| No hardcoded AMI IDs | `get_latest_ami` in `aws/ec2.py` | AMI ID is read from SSM Parameter Store at runtime |

## Tagging convention

Every resource created by this tool gets four tags:

| Tag | Example | Why |
| --- | --- | --- |
| `CreatedBy` | `platform-cli` | which tool made it |
| `Owner` | `rotem` | which person made it |
| `Project` | `AWS-CLI-PYTHON` | which project it belongs to |
| `Environment` | `dev` | which environment it belongs to |

Every read and every write filters on `CreatedBy` **and** `Owner`. That
combination is what makes the tool safe in a shared account: `CreatedBy` alone would match every person running the same exercise on a shared AWS account, and the tool would happily stop their instances.

Tagging happens differently on each service:

- **EC2** tags at launch, in the same API call, via `TagSpecifications`
- **S3** and **Route53** have no way to tag during creation, so the tool creates the resource first and tags it in a second call

## Cleanup

Resources cost money while they exist. To remove everything:

```bash
# instances - stop them, or terminate from the AWS CLI
python main.py ec2 list
python main.py ec2 stop --id i-0123456789abcdef0
aws ec2 terminate-instances --instance-ids i-0123456789abcdef0

# buckets - empty first, then remove
python main.py s3 list
aws s3 rm s3://my-bucket-name --recursive
aws s3 rb s3://my-bucket-name

# route53 - delete the records first, then the zone
python main.py route53 list
python main.py route53 list --zone-id Z0123456789ABCDEFGHIJ
python main.py route53 delete --zone-id Z0123456789ABCDEFGHIJ \
  --record-name www.example.com --record-value 1.2.3.4
python main.py route53 delete --zone-id Z0123456789ABCDEFGHIJ
```

Stopped instances still keep their disk, so they still cost a little. Terminate them if you are really finished.

## Design decisions

**Tags are a safety boundary, not a security boundary.** IAM decides what you *can* do. Tags decide what this tool *will* do. If your permissions allow it, you could still delete anything directly with the AWS CLI — the tag filter just means this tool will not do it by accident.

**The instance cap counts `pending`, not only `running`.** An instance that is still booting is real and already billable. Counting only `running` would let you launch a third machine in the gap.

**AMI IDs are looked up at runtime.** A hardcoded AMI ID is wrong in every other region and goes stale on the next security patch. SSM Parameter Store publishes the current ID at a fixed path, so the tool asks for "latest Ubuntu" version instead of naming a specific image.

**Validation happens before AWS calls.** Instance type and the running count are checked locally first, so a rejected request costs nothing and leaves nothing half-created.

**Prompts only for irreversible actions.** Making a bucket public and deleting a hosted zone ask for confirmation. Everything else is a flag with a sensible default, so the tool still works inside a script or a pipeline.

**Business logic is separate from the CLI.** `main.py` only parses arguments and prints. All the rules live in `aws/ec2.py`, `aws/s3.py` and `aws/route53.py`, so a future web UI can import the same functions and get the same guardrails without duplicating them.

## Known limitations

- Bucket creation assumes the `us-east-1` region. Other regions need a
  `CreateBucketConfiguration` parameter, which is not implemented yet.
- S3 and Route53 tag their resources in a second API call. If that call    fails, the resource exists but is untagged, which means this tool can no longer see or manage it. There is no rollback.
- Records are always created as type `A` with a TTL of 300. Other record types are not supported.
- Ownership is enforced by this tool only. It is not backed by IAM policy.

## Continuous integration

Every push and pull request runs a GitHub Actions workflow
(`.github/workflows/ci.yml`) that checks:

- `ruff check .` — linting, unused variables, undefined names, import order
- `black --check .` — formatting
- `python -m compileall .` — syntax

The `master` branch is protected and requires this check to pass, so changes go through a pull request rather than a direct push.

## Project structure

```
aws-cli-python/
├── main.py                     CLI entry point: argument parsing and routing
├── config.py                   all policy constants and tag definitions
├── check_aws_connectivity.py   prints your AWS account ID as a setup check
├── aws/
│   ├── ec2.py                  EC2 logic and guardrails
│   ├── s3.py                   S3 logic and guardrails
│   └── route53.py              Route53 logic and guardrails
├── requirements.txt
└── .github/workflows/ci.yml
```
