# VPS Configuration Management

# List all available commands
default:
    @just --list

# Run all validation tests (fast mode - skips Docker pulls)
validate:
    @echo "🔍 Running validation tests..."
    SKIP_DOCKER_PULL=true uv run validate

# Run full validation including Docker image pulls
validate-full:
    @echo "🔍 Running full validation tests..."
    uv run validate

# Test configuration locally with Docker
test-local:
    @echo "🧪 Testing configuration locally..."
    uv run test-local

# Clean up local test environment
test-clean:
    @echo "🧹 Cleaning up test environment..."
    cd docker/test-environment && docker-compose down --remove-orphans -v

# Setup inventory file (copy and customize)
setup:
    @echo "⚙️ Setting up inventory file..."
    @if [ ! -f ansible/inventories/production.yml ]; then \
        cp ansible/inventories/hosts.yml ansible/inventories/production.yml; \
        echo "✅ Created production.yml - please customize with your VPS IP and domain"; \
    else \
        echo "⚠️  production.yml already exists"; \
    fi

# Deploy all services to VPS
deploy:
    @echo "🚀 Deploying to VPS..."
    cd ansible && ansible-playbook playbooks/site.yml -i inventories/production.yml

# Deploy all services to VPS with verbose output
deploy-verbose:
    @echo "🚀 Deploying to VPS (verbose)..."
    cd ansible && ansible-playbook playbooks/site.yml -i inventories/production.yml -v

# Check Ansible syntax
check:
    @echo "🔍 Checking Ansible syntax..."
    cd ansible && ansible-playbook playbooks/site.yml --syntax-check -i inventories/production.yml

# Run Ansible in dry-run mode
dry-run:
    @echo "🧪 Running Ansible dry-run..."
    cd ansible && ansible-playbook playbooks/site.yml -i inventories/production.yml --check

# Test VPS connectivity
ping:
    @echo "📡 Testing VPS connectivity..."
    cd ansible && ansible vps -i inventories/production.yml -m ping

# Run health checks
health-check:
    @echo "🔍 Running health checks..."
    uv run health-check production

# Restart specific service
restart service:
    @echo "🔄 Restarting {{service}}..."
    cd ansible && ansible vps -i inventories/production.yml -m shell -a "docker restart {{service}}"

# View service logs
logs service:
    @echo "📋 Viewing {{service}} logs..."
    cd ansible && ansible vps -i inventories/production.yml -m shell -a "docker logs --tail 50 {{service}}"

# Clean temporary files
clean:
    @echo "🧹 Cleaning temporary files..."
    find . -name "*.retry" -delete

# Update Caddyfile only
update-caddy:
    @echo "🔄 Updating Caddyfile..."
    @echo "📄 Generating and copying Caddyfile..."
    cd ansible && ansible vps -i inventories/production.yml -m template -a "src=roles/caddy/templates/Caddyfile.j2 dest=/opt/caddy/Caddyfile mode=0644" --become
    @echo "🔄 Restarting Caddy container..."
    cd ansible && ansible vps -i inventories/production.yml -m docker_container -a "name=caddy restart=yes" --become

# Deploy Authelia only
deploy-authelia:
    @echo "🔒 Deploying Authelia..."
    cd ansible && ansible-playbook playbooks/site.yml -i inventories/production.yml --tags authelia

# Deploy Grafana only
deploy-grafana:
    @echo "📊 Deploying Grafana..."
    cd ansible && ansible-playbook playbooks/site.yml -i inventories/production.yml --tags grafana

# Reset Authelia user bans and regulation
reset-authelia-bans:
    @echo "🔓 Resetting Authelia bans..."
    cd ansible && ansible vps -i inventories/production.yml -m shell -a "docker exec authelia rm -f /data/db.sqlite3"
    @echo "🔄 Restarting Authelia..."
    cd ansible && ansible vps -i inventories/production.yml -m shell -a "docker restart authelia"
    @echo "✅ Authelia bans cleared and service restarted"

# SSH to VPS
ssh:
    @echo "🔐 Connecting to VPS..."
    cd ansible && ansible vps -i inventories/production.yml -m shell -a "uptime"

@authelia-hash password:
  docker run --rm authelia/authelia:latest authelia crypto hash generate --password '{{password}}'
