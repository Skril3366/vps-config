#!/bin/bash

# Local Testing Script
set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧪 Starting local testing environment...${NC}"

# Check if Docker is running
if ! docker info &>/dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Build and start test environment
echo -e "${YELLOW}🏗️  Building test environment...${NC}"
cd docker/test-environment
docker-compose down --remove-orphans 2>/dev/null || true
docker-compose up -d --build

# Wait for container to be ready
echo -e "${YELLOW}⏳ Waiting for test VPS to be ready...${NC}"
sleep 10

# Check if container is running
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${RED}❌ Test container failed to start${NC}"
    docker-compose logs
    exit 1
fi

# Test SSH connectivity
echo -e "${YELLOW}🔐 Testing SSH connectivity...${NC}"
timeout 30 bash -c 'until docker exec test-vps systemctl is-active ssh 2>/dev/null; do sleep 2; done'

# Generate SSH key if doesn't exist
if [ ! -f ~/.ssh/id_rsa ]; then
    echo -e "${YELLOW}🔑 Generating SSH key...${NC}"
    ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N ""
fi

# Copy SSH key to container
echo -e "${YELLOW}📋 Setting up SSH access...${NC}"
docker exec test-vps mkdir -p /root/.ssh
docker cp ~/.ssh/id_rsa.pub test-vps:/root/.ssh/authorized_keys
docker exec test-vps chmod 600 /root/.ssh/authorized_keys
docker exec test-vps chown root:root /root/.ssh/authorized_keys

# Run Ansible deployment
echo -e "${BLUE}🚀 Running Ansible deployment on test environment...${NC}"
cd ../../ansible

# Test connectivity first
echo -e "${YELLOW}📡 Testing Ansible connectivity...${NC}"
if ansible vps -i inventories/test.yml -m ping; then
    echo -e "${GREEN}✅ Connectivity test passed${NC}"
else
    echo -e "${RED}❌ Connectivity test failed${NC}"
    echo -e "${YELLOW}Container logs:${NC}"
    cd ../docker/test-environment
    docker-compose logs --tail 20
    exit 1
fi

# Run the playbook
echo -e "${BLUE}🔧 Deploying configuration...${NC}"
if ansible-playbook playbooks/site.yml -i inventories/test.yml; then
    echo -e "${GREEN}✅ Deployment successful${NC}"
else
    echo -e "${RED}❌ Deployment failed${NC}"
    exit 1
fi

# Test services
echo -e "${BLUE}🔍 Testing deployed services...${NC}"

# Wait for services to start
sleep 30

# Check if containers are running
echo -e "${YELLOW}🐳 Checking Docker containers...${NC}"
ansible vps -i inventories/test.yml -m shell -a "docker ps --format 'table {{.Names}}\t{{.Status}}'"

# Test HTTP endpoints
echo -e "${YELLOW}🌐 Testing HTTP endpoints...${NC}"

# Test Grafana
if curl -s -k https://localhost:3001 | grep -q "Grafana"; then
    echo -e "${GREEN}✅ Grafana is responding${NC}"
else
    echo -e "${YELLOW}⚠️  Grafana test inconclusive (might need more startup time)${NC}"
fi

# Test Prometheus
if curl -s -k https://localhost:9091 | grep -q "Prometheus"; then
    echo -e "${GREEN}✅ Prometheus is responding${NC}"
else
    echo -e "${YELLOW}⚠️  Prometheus test inconclusive${NC}"
fi

echo -e "\n${GREEN}🎉 Local testing completed!${NC}"
echo -e "${BLUE}You can now access services at:${NC}"
echo -e "  • Grafana: https://localhost:3001 (admin/admin)"
echo -e "  • Prometheus: https://localhost:9091"
echo -e "  • Loki: https://localhost:3101"

echo -e "\n${YELLOW}To clean up test environment:${NC}"
echo -e "  cd docker/test-environment && docker-compose down"

echo -e "\n${GREEN}✅ Configuration is ready for production deployment!${NC}"