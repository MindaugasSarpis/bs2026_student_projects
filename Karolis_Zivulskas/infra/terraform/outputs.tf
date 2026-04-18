output "public_ip" {
  description = "Elastic IP of the RepOps server"
  value       = aws_eip.app.public_ip
}

output "ssh_command" {
  description = "Command to SSH into the instance"
  value       = "ssh ubuntu@${aws_eip.app.public_ip}"
}

output "api_url" {
  description = "RepOps API URL"
  value       = "http://${aws_eip.app.public_ip}:8000"
}

output "grafana_url" {
  description = "Grafana dashboard URL (admin / repops)"
  value       = "http://${aws_eip.app.public_ip}:3000"
}

output "flower_url" {
  description = "Flower Celery task monitor URL"
  value       = "http://${aws_eip.app.public_ip}:5555"
}

