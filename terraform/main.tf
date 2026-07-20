terraform {
    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "~> 5.92"
            }
        local = {
            source = "hashicorp/local"
            }
        random = {
            source = "hashicorp/random"
            }

    }

    required_version = ">= 1.2"
}

resource "random_string" "bucket_suffix" {
    length  = 6
    upper   = false
    special = false
}

provider "aws" {
    region = "us-west-2"

    default_tags {
        tags = {
            Project     = "palms"
            Environment = "production"
            ManagedBy   = "Terraform"
        }
    }

}
######################################
## Key pair

variable "public_key_path" {

    description = "Path to the local SSH public key."
    type = string
}

resource "aws_key_pair" "baytak_key" {

    key_name = "palm-key-pair"
    public_key = file(var.public_key_path)


    tags = {
        Name = "palms-production"
    }

}


#######################################
## EC2

locals {
    instances = {
        p1 = {}
        p2 = {}
        p3 = {}
    }
}
resource "aws_instance" "palms" {

    for_each = local.instances

    ami = data.aws_ami.ubuntu.id

    instance_type = "m7i-flex.large"

    key_name = aws_key_pair.baytak_key.key_name
    associate_public_ip_address = true

    iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

    root_block_device {

        volume_size = 30

        volume_type = "gp3"

        encrypted = true

        delete_on_termination = true

    }
    vpc_security_group_ids = [

        aws_security_group.palms_sg.id

    ]
    monitoring = false

    disable_api_termination = false

    instance_initiated_shutdown_behavior = "stop"

    user_data= <<-EOF
    #!/bin/bash
    apt-get update -y
    echo "Instance Started"

    EOF

    tags = {
        Name = "palms-server-${each.key}"
    }

}


data "aws_ami" "ubuntu" {

    most_recent = true

    # Canonical (Ubuntu) AWS Account ID
    owners = ["099720109477"]

    # Filter by image name
    filter {
        name = "name"
        values = [
        "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"
        ]

    }
    # Only HVM virtualization

    filter {
        name = "virtualization-type"
        values = ["hvm"]

    }

}


resource "local_file" "instance_ip" {
    filename = "${path.module}/../instance_ip"
    content = join("\n", values(aws_instance.palms)[*].public_ip)
}


resource "local_file" "ansible_inventory" {
    filename = "${path.module}/../ansible/inventory.ini"

    content = join("\n", concat(
        ["[servers]"],
        [
            for name, instance in aws_instance.palms :
            "${name} ansible_host=${instance.public_ip} k3s_ip=${instance.private_ip} ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/id_rsa"
        ],
        [""]
    ))
}

########################################
## IAM 

resource "aws_iam_role" "ec2_s3_role" {

    name = "palms-production-ec2-role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
        {
            Action = "sts:AssumeRole"
            Effect = "Allow"
            Principal = {
            Service = "ec2.amazonaws.com"
            }
        }
        ]
    })
    tags = {
        Name = "palms-production"
    }
}

resource "aws_iam_role_policy_attachment" "s3_full_access_attach" {
    role       = aws_iam_role.ec2_s3_role.name
    policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# resource "aws_iam_role_policy_attachment" "s3_access_attach" {
#     role       = aws_iam_role.ec2_s3_role.name
#     policy_arn = "arn:aws:s3:::palms-bucket/*"
# }



resource "aws_iam_instance_profile" "ec2_profile" {

    name = "palms-production-instance-profile"

    role = aws_iam_role.ec2_s3_role.name

}

data "aws_vpc" "default" {
    default = true
}

resource "aws_security_group" "palms_sg" {
    name        = "palms-sg"
    description = "Security group for palms server"
    vpc_id      = data.aws_vpc.default.id

    ingress {
        description = "SSH"
        from_port   = 22
        to_port     = 22
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

    ingress {
        description = "Application HTTP"
        from_port   = 80
        to_port     = 80
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

    ingress {
        description = "Application HTTPS"
        from_port   = 443
        to_port     = 443
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

    ingress {
    description = "Kubernetes API between cluster nodes"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    self        = true
    }

    ingress {
    description = "etcd"
    from_port   = 2379
    to_port     = 2380
    protocol    = "tcp"
    self        = true
    }

    ingress {
    description = "Flannel VXLAN"
    from_port   = 8472
    to_port     = 8472
    protocol    = "udp"
    self        = true
    }

    ingress {
        description = "Kubelet between cluster nodes"
        from_port   = 10250
        to_port     = 10250
        protocol    = "tcp"
        self        = true
    }

    egress {
        description = "Allow all outbound traffic"
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }

    tags = {
        Name = "palms-sg"
    }
}

output "instance_ips" {
    value = {
        for name, instance in aws_instance.palms :
        name => instance.public_ip
    }
}


###################################
## s3

resource "aws_s3_bucket" "palms-bucket" {
    bucket = "palms-projects-bucket-${random_string.bucket_suffix.result}"

    tags = {
        Name        = "My bucket"
        Environment = "Dev"
    }
}