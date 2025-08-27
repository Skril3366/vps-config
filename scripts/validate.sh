#!/bin/bash

# VPS Configuration Validation Script
set -e

echo "🔍 Running pre-deployment validation..."

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing $test_name... "
    
    if eval "$test_command" &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Check prerequisites
echo "📋 Checking prerequisites..."
run_test "Ansible installation" "command -v ansible-playbook"
run_test "Docker installation (for local testing)" "command -v docker"
run_test "uv installation" "command -v uv"
run_test "Python docker module" "python3 -c 'import docker'"

# Check file structure
echo -e "\n📁 Checking file structure..."
run_test "Main playbook exists" "test -f ansible/playbooks/site.yml"
run_test "Inventory template exists" "test -f ansible/inventories/hosts.yml"
run_test "Caddy role exists" "test -f ansible/roles/caddy/tasks/main.yml"
run_test "Docker role exists" "test -f ansible/roles/docker/tasks/main.yml"
run_test "Monitoring role exists" "test -f ansible/roles/monitoring/tasks/main.yml"
run_test "Caddyfile template exists" "test -f ansible/roles/caddy/templates/Caddyfile.j2"

# Ansible syntax validation
echo -e "\n🔍 Validating Ansible syntax..."
if test -f ansible/inventories/production.yml; then
    INVENTORY="ansible/inventories/production.yml"
else
    echo -e "${YELLOW}⚠️  Using template inventory for syntax check${NC}"
    INVENTORY="ansible/inventories/hosts.yml"
fi

run_test "Playbook syntax" "cd ansible && ansible-playbook playbooks/site.yml --syntax-check -i $INVENTORY"

# Template rendering test (skip if using template inventory)
if [[ "$INVENTORY" == *"hosts.yml" ]]; then
    echo -e "\n🎨 Skipping template rendering test (using template inventory)"
else
    echo -e "\n🎨 Testing template rendering..."
    run_test "Caddyfile template syntax" "cd ansible && ansible-playbook playbooks/site.yml --check -i $INVENTORY -t caddy --diff"
fi

# Docker image availability (optional - can be slow)
if [[ "${SKIP_DOCKER_PULL:-}" != "true" ]]; then
    echo -e "\n🐳 Checking Docker image availability..."
    echo -e "${YELLOW}💡 Tip: Set SKIP_DOCKER_PULL=true to skip image pulling${NC}"
    IMAGES=(
        "caddy:2-alpine"
        "prom/prometheus:latest"
        "prom/node-exporter:latest"
        "grafana/grafana:latest"
        "grafana/loki:latest"
        "grafana/promtail:latest"
    )

    for image in "${IMAGES[@]}"; do
        run_test "Docker image: $image" "docker pull $image"
    done
else
    echo -e "\n🐳 Skipping Docker image pulls (SKIP_DOCKER_PULL=true)"
fi

# Configuration validation
echo -e "\n⚙️  Validating configuration files..."
if python3 -c "import yaml" 2>/dev/null; then
    run_test "Prometheus config template" "cd ansible/roles/monitoring/templates && python3 -c 'import yaml; yaml.safe_load(open(\"prometheus.yml.j2\").read())'"
    run_test "Loki config template" "cd ansible/roles/monitoring/templates && python3 -c 'import yaml; yaml.safe_load(open(\"loki.yml.j2\").read())'"
    run_test "Promtail config template" "cd ansible/roles/monitoring/templates && python3 -c 'import yaml; yaml.safe_load(open(\"promtail.yml.j2\").read())'"
else
    echo -e "${YELLOW}⚠️  PyYAML not available in system Python, skipping YAML validation${NC}"
    echo -e "${YELLOW}💡 Install dependencies with: uv pip install -r requirements.txt${NC}"
fi

# Summary
echo -e "\n📊 Test Summary:"
echo -e "✅ Passed: $TESTS_PASSED"
echo -e "❌ Failed: $TESTS_FAILED"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All validation tests passed! Ready for deployment.${NC}"
    exit 0
else
    echo -e "\n${RED}💥 Some validation tests failed. Please fix issues before deployment.${NC}"
    exit 1
fi