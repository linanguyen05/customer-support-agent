output "ec2_public_ip" {
  value = aws_eip.agent.public_ip
}

output "ec2_public_dns" {
  value = aws_eip.agent.public_dns
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/ck.pem ubuntu@${aws_eip.agent.public_ip}"
}

output "streamlit_url" {
  value = "http://${aws_eip.agent.public_ip}:8501"
}