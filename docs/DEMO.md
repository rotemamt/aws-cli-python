# Demo Evidence

Terminal output from a real run against a shared AWS account used by the whole
class. Every command below is the tool itself, not the AWS CLI, unless noted.

---

## The CLI itself

```
$ python main.py --help
usage: main.py [-h] [--type {t3.micro,t2.small}] [--os {ubuntu,amazon-linux}] [--id ID]
               [--name NAME] [--file FILE] [--public] [--zone-id ZONE_ID]
               [--record-name RECORD_NAME] [--record-value RECORD_VALUE]
               {ec2,s3,route53} {list,create,stop,start,update,upload,delete}

AWS self-service CLI tool

positional arguments:
  {ec2,s3,route53}      Which AWS service to use
  {list,create,stop,start,update,upload,delete}
                        Action to perform on the resource

options:
  -h, --help            show this help message and exit
  --type {t3.micro,t2.small}
                        EC2 instance type
  --os {ubuntu,amazon-linux}
                        Operating system
  --id ID               Instance ID
  --name NAME           The Bucket name
  --file FILE           Path to the file to upload
  --public              Make the S3 Bucket public
  --zone-id ZONE_ID     Route53 hosted zone ID
  --record-name RECORD_NAME
                        DNS record name, e.g. www.example.com
  --record-value RECORD_VALUE
                        DNS record value, e.g. an IPv4 address
```

Proves: every command takes the same shape — resource, action, then parameters.
The allowed instance types shown in `--type` come from `config.py`, so changing
the policy in one place updates the help text automatically.

---

## EC2

### Create, list, stop, start

```
$ python main.py ec2 create --type t3.micro --os ubuntu
Instance Id: i-06cd57b8a9d48b0dd, Instance type: t3.micro, AMI: ami-06e78a71af43ef21a

$ python main.py ec2 list
i-06cd57b8a9d48b0dd t3.micro running

$ python main.py ec2 stop --id i-06cd57b8a9d48b0dd
Stopping i-06cd57b8a9d48b0dd

$ python main.py ec2 list
i-06cd57b8a9d48b0dd t3.micro stopping

$ python main.py ec2 list
i-06cd57b8a9d48b0dd t3.micro stopped

$ python main.py ec2 start --id i-06cd57b8a9d48b0dd
Starting i-06cd57b8a9d48b0dd

$ python main.py ec2 list
i-06cd57b8a9d48b0dd t3.micro running
```

Proves: the instance is created with an AMI resolved from SSM at runtime (never
hardcoded), `list` shows only instances this CLI created, and stop/start really
change the state. The intermediate `stopping` line shows that AWS calls are
asynchronous — the API returns before the machine has finished changing state.

### Guardrail: only approved instance types

```
$ python main.py ec2 create --type m5.large
usage: main.py [-h] [--type {t3.micro,t2.small}] [--os {ubuntu,amazon-linux}] [--id ID]
               [--name NAME] [--file FILE] [--public] [--zone-id ZONE_ID]
               [--record-name RECORD_NAME] [--record-value RECORD_VALUE]
               {ec2,s3,route53} {list,create,stop,start,update,upload,delete}
main.py: error: argument --type: invalid choice: 'm5.large' (choose from t3.micro, t2.small)
```

Proves: an expensive instance type is rejected at the CLI layer, before any AWS
call is made. The same check also exists inside `create_instance`, so a future
web UI cannot bypass it.

### Guardrail: maximum 2 running instances

```
$ python main.py ec2 create --type t2.small --os amazon-linux
Instance Id: i-0d360c7549e4f20df, Instance type: t2.small, AMI: ami-07a5b367e8dc8bd92

$ python main.py ec2 create --type t3.micro
Error: 2 are already running, you've hit the limit.
```

Proves: the cap is enforced by counting tagged instances in `running` **or**
`pending` before creating. Nothing is launched, so the rejected request costs
nothing. The second command also demonstrates the `t2.small` and `amazon-linux`
paths, which resolve a different AMI.

### Guardrail: only touch resources this CLI created

```
$ python main.py ec2 stop --id i-070e2376ee89fda8e
Error: i-070e2376ee89fda8e was not created by this CLI. Refusing to stop it.
```

Proves: `i-070e2376ee89fda8e` belongs to another student in the same AWS
account and carries `CreatedBy=platform-cli` — but not `Owner=rotem`. Filtering
on both tags is what makes the tool safe in a shared account.

### Readable errors for missing arguments

```
$ python main.py ec2 stop
Error: --id is required for start and stop
```

Proves: missing arguments produce one clear line and a non-zero exit code,
not a Python traceback.

### A note on EC2 cleanup

The CLI deliberately has no terminate action for EC2. `stop` is reversible and
enough for day-to-day use; terminating destroys the instance and its root volume
permanently, so it is left to an explicit AWS CLI call:

```
$ aws ec2 terminate-instances --instance-ids i-06cd57b8a9d48b0dd
```

Terminated instances are excluded from `list`, which only shows instances in
`pending`, `running`, `stopping` or `stopped` — a developer wants the machines
that exist, not the ones AWS is still cleaning up.

---

## S3

### Create a private bucket, upload, list

```
$ echo "hello" > /tmp/test.txt

$ python main.py s3 create --name rotem-private-2026
Created bucket rotem-private-2026

$ python main.py s3 upload --name rotem-private-2026 --file /tmp/test.txt
Uploaded test.txt to rotem-private-2026

$ python main.py s3 list
rotem-private-2026
```

Proves: private is the default, the bucket is tagged at creation, and `list`
finds it again by those tags. The account contains more than 20 buckets from
other students; only this one is shown.

### Guardrail: public buckets require confirmation

```
$ python main.py s3 create --name rotem-public-2026 --public
Make this bucket PUBLIC? Type yes to confirm: no
Aborted

$ python main.py s3 create --name rotem-public-2026 --public
Make this bucket PUBLIC? Type yes to confirm: y
Created bucket rotem-public-2026
```

Proves: exposing a bucket to the internet cannot happen by accident. Anything
other than an explicit confirmation aborts before any AWS call.

### Public vs private, verified from outside AWS

```
$ python main.py s3 upload --name rotem-public-2026 --file /tmp/test.txt
Uploaded test.txt to rotem-public-2026

$ curl https://rotem-public-2026.s3.amazonaws.com/test.txt
hello

$ curl https://rotem-private-2026.s3.amazonaws.com/test.txt
<?xml version="1.0" encoding="UTF-8"?>
<Error><Code>AccessDenied</Code><Message>Access Denied</Message>...</Error>
```

Proves: the `--public` flag really works. Same URL shape, same file, opposite
results — one anonymous request succeeds, the other is denied. The public bucket
needed both its Block Public Access settings disabled and a bucket policy
granting `s3:GetObject` to `*`.

### Guardrail: cannot upload into someone else's bucket

```
$ python main.py s3 upload --name yaara-test-bucket-2202 --file /tmp/test.txt
Error: yaara-test-bucket-2202 was not created by this CLI.
```

Proves: the tag check runs before the upload, so the file is never sent.

---

## Route53

### Create a zone, list zones

```
$ python main.py route53 create --name rotem-demo.com
'rotem-demo.com' created. zone id: 'Z071193220P1GWT33UY7T'

$ python main.py route53 list
rotem-demo.com. Z071193220P1GWT33UY7T
```

Proves: the zone is created and then tagged in a second call, because Route53
has no way to tag during creation. `list` filters client-side on those tags —
the account has 12 hosted zones and only this one is shown.

### Create, list, update a DNS record

```
$ python main.py route53 create --zone-id Z071193220P1GWT33UY7T \
    --record-name www.rotem-demo.com --record-value 1.2.3.4
UPSERT www.rotem-demo.com -> 1.2.3.4

$ python main.py route53 list --zone-id Z071193220P1GWT33UY7T
www.rotem-demo.com. A 1.2.3.4

$ python main.py route53 update --zone-id Z071193220P1GWT33UY7T \
    --record-name www.rotem-demo.com --record-value 5.6.7.8
UPSERT www.rotem-demo.com -> 5.6.7.8

$ python main.py route53 list --zone-id Z071193220P1GWT33UY7T
www.rotem-demo.com. A 5.6.7.8
```

Proves: create and update both use `UPSERT`, so the second call overwrites the
record instead of creating a duplicate. The two `list` calls either side of the
update show the value actually changed. `list` skips the automatic `NS` and
`SOA` records that every zone gets.

### Guardrail: unknown zone ID

```
$ python main.py route53 list --zone-id ZBOGUS123
Error: no hosted zone found with ID ZBOGUS123
```

Proves: a typo'd zone ID produces one readable line instead of a
`NoSuchHostedZone` traceback.

### Guardrail: cannot read another student's zone

```
$ aws route53 list-hosted-zones --query "HostedZones[].[Id,Name]" --output text
/hostedzone/Z0108436IXZEJBB3AIL9   stav-platform-cli-exam.test.
/hostedzone/Z01005591NOWIFWOS92BA  demo.stav-platform-cli-exam.test.
/hostedzone/Z09223032NEK2O06QX9AO  aviv-platform-cli.example.
/hostedzone/Z071193220P1GWT33UY7T  rotem-demo.com.
/hostedzone/Z0038353LTI2VEC4MZJ6   yaaratestpython.com.
...

$ python main.py route53 list --zone-id Z01005591NOWIFWOS92BA
Error: zone Z01005591NOWIFWOS92BA was not created by this CLI.
```

Proves: ownership is checked *before* the records are fetched, so the tool never
reads data from a zone it does not own.

### Delete a record, then the zone

```
$ python main.py route53 delete --zone-id Z071193220P1GWT33UY7T \
    --record-name www.rotem-demo.com --record-value 5.6.7.8
DELETE www.rotem-demo.com -> 5.6.7.8

$ python main.py route53 delete --zone-id Z071193220P1GWT33UY7T
Are you sure you want to delete? Type yes to confirm: no
Aborted

$ python main.py route53 delete --zone-id Z071193220P1GWT33UY7T
Are you sure you want to delete? Type yes to confirm: yes
Z071193220P1GWT33UY7T was deleted
```

Proves: deleting a zone is irreversible, so it asks first. The record has to go
first — AWS refuses to delete a zone that still contains records, and that error
is caught and printed readably:

```
Error deleting zone: An error occurred (HostedZoneNotEmpty) when calling the
DeleteHostedZone operation: The specified hosted zone contains non-required
resource record sets and so cannot be deleted.
```

Deleting a record requires an exact match on name, type, TTL and value — which
is why `--record-value` is required even for a delete.

---

## CI and branch protection

Every push and pull request runs lint, format and syntax checks.

Direct pushes to `master` are rejected:

```
$ git push
remote: error: GH006: Protected branch update failed for refs/heads/master.
remote:
remote: - Required status check "code-quality-check" is expected.
To https://github.com/rotemamt/aws-cli-python.git
 ! [remote rejected] master -> master (protected branch hook declined)
error: failed to push some refs to 'https://github.com/rotemamt/aws-cli-python.git'
```

Proves: changes must go through a pull request whose CI check passes before it
can be merged.

CI also caught a real defect during development — `ruff` reported an unused
variable in `change_record`, which turned out to be a missing zone-ownership
check that would have let the tool edit DNS records in other students' zones.
