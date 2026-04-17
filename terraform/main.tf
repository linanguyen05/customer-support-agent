terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Sử dụng bucket đã tồn tại
data "aws_s3_bucket" "data" {
  bucket = var.s3_bucket_name
}

# Elastic IP
resource "aws_eip" "agent" {
  domain = "vpc"
  tags = {
    Name = "customer-support-agent-eip"
  }
}

# Security Group
resource "aws_security_group" "agent_sg" {
  name        = "customer-support-agent-sg"
  description = "Allow SSH and Streamlit"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH from anywhere (temporary)"
  }

  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Streamlit UI"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# IAM Role cho EC2 để truy cập S3 và Bedrock
resource "aws_iam_role" "ec2_role" {
  name = "ec2-bedrock-s3-role"
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
}

resource "aws_iam_role_policy" "ec2_policy" {
  name = "ec2-bedrock-s3-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          data.aws_s3_bucket.data.arn,
          "${data.aws_s3_bucket.data.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ec2-bedrock-s3-profile"
  role = aws_iam_role.ec2_role.name
}

# User data script (template)
# Không cần data template_file nữa, dùng templatefile trực tiếp 

# EC2 Instance
resource "aws_instance" "agent" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.agent_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  user_data_base64 = base64encode(templatefile("${path.module}/user_data.sh.tpl", {
    S3_BUCKET          = var.s3_bucket_name
    GITHUB_REPO_URL    = var.github_repo_url
    GITHUB_BRANCH      = var.github_branch
    GITHUB_ACTIONS_PUB_KEY = var.github_actions_public_key
    AWS_REGION         = var.aws_region
  }))

  tags = {
    Name = "customer-support-agent"
  }
}

# Gắn Elastic IP
resource "aws_eip_association" "agent_eip" {
  instance_id   = aws_instance.agent.id
  allocation_id = aws_eip.agent.id
}

# Lấy AMI Ubuntu 22.04 mới nhất
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}