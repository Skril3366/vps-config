# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Ansible-based VPS configuration project that sets up a personal server with:
- **Caddy**: Reverse proxy with automatic HTTPS
- **Docker**: Container runtime for all services  
- **Monitoring Stack**: Prometheus, Grafana, Loki, Promtail for comprehensive observability
- **Security**: SSH hardening, firewall rules, fail2ban protection
- **Keycloak**: Identity and access management (currently disabled due to resource usage)
- **Portainer**: Docker management UI (placeholder, not yet implemented)

## Common Commands

All commands should be run from the project root directory.

### Development & Testing Commands
```bash
# Install dependencies
uv sync

# Run validation tests (fast - skips Docker pulls)
just validate
# or: uv run validate

# Run full validation including Docker image pulls  
just validate-full
# or: uv run validate

# Test configuration locally with Docker
just test-local
# or: uv run test-local

# Clean up local test environment
just test-clean
```

### Deployment Commands
```bash
# Setup production inventory file (copy template)
just setup

# Check Ansible syntax
just check
# or: uv run deploy production check

# Test deployment without making changes
just dry-run
# or: uv run deploy production plan

# Deploy to VPS
just deploy
# or: uv run deploy production apply

# Deploy with verbose Ansible output
just deploy-verbose
```

### Management Commands
```bash
# Test VPS connectivity
just ping

# Run comprehensive health checks
just health-check
# or: uv run health-check production

# Restart specific service (e.g., grafana, prometheus)
just restart grafana

# View service logs (e.g., prometheus, loki)
just logs prometheus

# Quick VPS connection test
just ssh

# Clean temporary files
just clean
```

## Architecture

### Ansible Structure
- **Playbook**: `ansible/playbooks/site.yml` - Main orchestration
- **Roles**:
  - `common`: Basic system setup, packages, user management
  - `security`: SSH hardening, firewall rules, fail2ban
  - `docker`: Docker engine installation and configuration
  - `caddy`: Reverse proxy setup with automatic HTTPS
  - `monitoring`: Prometheus, Grafana, Loki stack deployment
  - `keycloak`: Identity and access management (disabled in playbook)
  - `portainer`: Docker management UI (placeholder, not implemented)

### Configuration Management
- **Inventory**: Use `ansible/inventories/hosts.yml` as template; create `production.yml` for actual deployment
- **Variables**: 
  - Global variables in `ansible/group_vars/all.yml`
  - Host-specific variables in `host_vars/` directories
- **Templates**: Jinja2 templates in each role's `templates/` directory

### Local Testing Environment  
- **Location**: `docker/test-environment/`
- **Purpose**: Test Ansible configurations locally using Docker container with systemd
- **Access**: Container exposes SSH on port 2222, services on mapped ports

## Key Files to Edit

### For VPS Configuration
- `ansible/inventories/production.yml`: Your VPS IP, SSH settings, domain name
- `ansible/group_vars/all.yml`: Global variables and service configuration
- `ansible/roles/caddy/templates/Caddyfile.j2`: Add reverse proxy rules for your applications

### For Service Configuration
- `ansible/roles/monitoring/templates/prometheus.yml.j2`: Prometheus scrape targets and configuration
- `ansible/roles/monitoring/templates/loki.yml.j2`: Loki configuration for log aggregation
- `ansible/roles/monitoring/templates/promtail.yml.j2`: Promtail configuration for log collection
- `docker/compose/monitoring.yml`: Docker Compose for monitoring stack

## Testing Workflow

1. **Validate**: Run `just validate` (fast) or `just validate-full` (comprehensive) to check syntax and prerequisites
2. **Local Test**: Run `just test-local` to deploy to Docker container with systemd simulation
3. **Syntax Check**: Run `just check` to verify Ansible playbook syntax
4. **Dry Run**: Run `just dry-run` to test deployment without making changes
5. **Production Deploy**: Run `just deploy` after successful testing

The local testing environment uses a Docker container with systemd to closely simulate the target VPS environment, including SSH access and service management.

## Python Scripts

All scripts are written in Python and use the uv package manager for dependency management:

- `scripts/validate.py`: Pre-deployment validation (syntax, prerequisites, Docker images)
- `scripts/test_local.py`: Local Docker-based testing with full deployment simulation  
- `scripts/deployment/deploy.py`: Ansible deployment wrapper with syntax checking, dry-run, and deployment
- `scripts/utilities/health_check.py`: Infrastructure health checks for connectivity, resources, services, and monitoring endpoints

All scripts provide colored output, detailed error reporting, and can be run via uv entry points:
- `uv run validate` - Run validation tests
- `uv run test-local` - Run local testing
- `uv run deploy <environment> <action>` - Deploy with Ansible (actions: check, plan, apply, cleanup)
- `uv run health-check <environment>` - Run health checks

## Service Access

After deployment, services are available at:

**Direct access** (using server IP and default ports from group_vars):
- **Grafana**: Port 3000 (default admin/admin - change on first login)
- **Prometheus**: Port 9090  
- **Loki**: Port 3100
- **Node Exporter**: Port 9100

**Domain access** (via Caddy reverse proxy):
URLs depend on your domain configuration in the Caddy template:
- `https://grafana.yourdomain.com`
- `https://prometheus.yourdomain.com`
- `https://loki.yourdomain.com`

**Configuration locations:**
- Port configurations: `ansible/group_vars/all.yml`
- Domain configurations: `ansible/roles/caddy/templates/Caddyfile.j2`