#!/bin/bash

# VPS Infrastructure Deployment Script
set -e

ENVIRONMENT=${1:-dev}
ACTION=${2:-plan}

echo "🚀 Starting deployment for environment: $ENVIRONMENT"

# Check prerequisites
command -v terraform >/dev/null 2>&1 || { echo "❌ Terraform is required but not installed."; exit 1; }
command -v ansible >/dev/null 2>&1 || { echo "❌ Ansible is required but not installed."; exit 1; }

# Navigate to terraform directory
cd "$(dirname "$0")/../../terraform"

# Initialize Terraform
echo "📦 Initializing Terraform..."
terraform init

# Select or create workspace for environment
if ! terraform workspace select "$ENVIRONMENT" 2>/dev/null; then
    echo "🏗️ Creating new workspace: $ENVIRONMENT"
    terraform workspace new "$ENVIRONMENT"
fi

# Terraform operations
case $ACTION in
    "plan")
        echo "📋 Planning infrastructure changes..."
        terraform plan -var-file="environments/$ENVIRONMENT/terraform.tfvars"
        ;;
    "apply")
        echo "🏗️ Applying infrastructure changes..."
        terraform apply -var-file="environments/$ENVIRONMENT/terraform.tfvars" -auto-approve
        
        echo "⚙️ Configuring servers with Ansible..."
        cd ../ansible
        ansible-playbook playbooks/site.yml -i "inventories/$ENVIRONMENT.yml"
        ;;
    "destroy")
        echo "💥 Destroying infrastructure..."
        cd ../ansible
        ansible-playbook playbooks/cleanup.yml -i "inventories/$ENVIRONMENT.yml" || true
        cd ../terraform
        terraform destroy -var-file="environments/$ENVIRONMENT/terraform.tfvars" -auto-approve
        ;;
    *)
        echo "❌ Invalid action: $ACTION"
        echo "Usage: $0 <environment> <plan|apply|destroy>"
        exit 1
        ;;
esac

echo "✅ Deployment completed successfully!"