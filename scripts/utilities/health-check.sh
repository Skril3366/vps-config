#!/bin/bash

# Infrastructure Health Check Script
set -e

ENVIRONMENT=${1:-dev}

echo "🔍 Running health checks for environment: $ENVIRONMENT"

# Check if servers are reachable
echo "📡 Checking server connectivity..."
cd "$(dirname "$0")/../../ansible"
ansible all -i "inventories/$ENVIRONMENT.yml" -m ping

# Check system resources
echo "💾 Checking system resources..."
ansible all -i "inventories/$ENVIRONMENT.yml" -m shell -a "df -h | head -5"
ansible all -i "inventories/$ENVIRONMENT.yml" -m shell -a "free -h"
ansible all -i "inventories/$ENVIRONMENT.yml" -m shell -a "uptime"

# Check services
echo "🔧 Checking critical services..."
ansible all -i "inventories/$ENVIRONMENT.yml" -m service -a "name=ssh state=started"

echo "✅ Health check completed!"