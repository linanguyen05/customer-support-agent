variable "aws_region" {
  description = "AWS region"
  default     = "us-east-1"
}

variable "instance_type" {
  default = "t2.micro"
}

variable "key_name" {
  description = "Name of existing EC2 Key Pair"
  default     = "ck"
}

variable "s3_bucket_name" {
  description = "Existing S3 bucket name for PDF and FAISS index"
  default     = "support-agent-data-la-ck"
}

variable "github_repo_url" {
  description = "GitHub repository URL (HTTPS)"
  default     = "https://github.com/linanguyen05/customer-support-agent.git"
}

variable "github_branch" {
  default = "main"
}

variable "github_actions_public_key" {
  description = "Public key (content) for GitHub Actions SSH access"
  sensitive   = true
}