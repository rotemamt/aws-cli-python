ALLOWED_INSTANCE_TYPES = ["t3.micro", "t2.small"]
MAX_RUNNING_INSTANCES = 2
CREATED_BY_TAG_KEY = "CreatedBy"
CREATED_BY_TAG_VALUE = "platform-cli"
OWNER_TAG_KEY = "Owner"
OWNER_TAG_VALUE = "rotem"
PROJECT_TAG_KEY = "Project"
PROJECT_TAG_VALUE = "AWS-CLI-PYTHON"
ENVIRONMENT_TAG_KEY = "Environment"
ENVIRONMENT_TAG_VALUE = "dev"
UBUNTU_AMI_PARAMETER = (
    "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
)
AMAZON_LINUX_AMI_PARAMETER = (
    "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
)
