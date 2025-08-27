# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Ansible-based VPS configuration project that sets up a personal server with:
- **Caddy**: Reverse proxy with automatic HTTPS
- **Docker**: Container runtime for all services  
- **Monitoring Stack**: Prometheus, Grafana, Loki, Promtail for metrics and logs
- **Security**: Basic hardening through the security role

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

# Test deployment without making changes
just dry-run

# Deploy to VPS
just deploy
```

### Management Commands
```bash
# Test VPS connectivity
just ping

# Check running containers on VPS
just health-check

# Restart specific service (e.g., grafana, prometheus)
just restart grafana

# View service logs (e.g., prometheus, loki)
just logs prometheus
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

### Configuration Management
- **Inventory**: Use `ansible/inventories/hosts.yml` as template; create `production.yml` for actual deployment
- **Variables**: Defined in `group_vars/` and `host_vars/` directories
- **Templates**: Jinja2 templates in each role's `templates/` directory

### Local Testing Environment  
- **Location**: `docker/test-environment/`
- **Purpose**: Test Ansible configurations locally using Docker container with systemd
- **Access**: Container exposes SSH on port 2222, services on mapped ports

## Key Files to Edit

### For VPS Configuration
- `ansible/inventories/production.yml`: Your VPS IP, SSH settings, domain name
- `ansible/roles/caddy/templates/Caddyfile.j2`: Add reverse proxy rules for your applications
- `ansible/group_vars/all.yml`: Global variables (if exists)

### For Service Configuration
- `ansible/roles/monitoring/templates/prometheus.yml.j2`: Prometheus scrape targets
- `ansible/roles/monitoring/templates/grafana-config.ini.j2`: Grafana configuration (if exists)
- `docker/compose/monitoring.yml`: Docker Compose for monitoring stack

## Testing Workflow

1. **Validate**: Run `just validate` to check syntax and prerequisites
2. **Local Test**: Run `just test-local` to deploy to Docker container
3. **Production Deploy**: Run `just deploy` after testing

The local testing environment uses Docker to simulate the target VPS environment, including systemd services and SSH access.

## Python Scripts

- `scripts/validate.py`: Pre-deployment validation (syntax, prerequisites, Docker images)
- `scripts/test_local.py`: Local Docker-based testing with full deployment simulation
- Both scripts provide colored output and detailed error reporting

## Service Access

After deployment, services are available at:
- **Grafana**: Port 3001 (default admin/admin)
- **Prometheus**: Port 9091  
- **Loki**: Port 3101

URLs depend on your domain configuration in the Caddy template.