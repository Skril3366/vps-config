# Personal VPS Configuration

Simple Ansible-based configuration for a personal VPS with monitoring and reverse proxy.

## What's Included

- **Caddy**: Reverse proxy with automatic HTTPS
- **Docker**: Container runtime for all services
- **Monitoring Stack**: Prometheus, Grafana, Loki, Promtail for comprehensive observability
- **Security**: SSH hardening, firewall rules, and fail2ban protection

## Repository Structure

```
├── ansible/
│   ├── roles/
│   │   ├── common/     # Basic system setup, packages, user management
│   │   ├── security/   # SSH hardening, firewall rules, fail2ban
│   │   ├── docker/     # Docker engine installation and configuration
│   │   ├── caddy/      # Reverse proxy setup with automatic HTTPS
│   │   ├── monitoring/ # Prometheus, Grafana, Loki stack deployment
│   │   └── portainer/  # Docker management UI (placeholder)
│   ├── playbooks/
│   │   └── site.yml    # Main orchestration playbook
│   ├── inventories/
│   │   ├── hosts.yml   # Server inventory template
│   │   ├── production.yml # Production environment config
│   │   └── test.yml    # Test environment config
│   └── group_vars/
│       └── all.yml     # Global variables and configuration
├── docker/
│   ├── compose/        # Docker Compose files
│   └── test-environment/ # Local testing infrastructure
├── scripts/            # Python automation scripts
│   ├── validate.py     # Pre-deployment validation
│   ├── test_local.py   # Local Docker-based testing
│   ├── deployment/     # Deployment utilities
│   └── utilities/      # Health checks and maintenance
├── justfile           # Task automation and shortcuts
└── pyproject.toml     # Python dependencies and project config
```

## Quick Start

### Prerequisites

- **just**: Task runner for command automation (`brew install just`)
- **uv**: Fast Python package manager (`brew install uv`)
- **Docker**: For local testing and containerization
- **SSH access** to your VPS with sudo privileges
- **Python 3.8+**: For running automation scripts

### Setup & Testing

1. **Initialize project and install dependencies**:
   ```bash
   uv sync
   ```

2. **Validate configuration**:
   ```bash
   just validate          # Fast validation (skips Docker pulls)
   just validate-full     # Full validation with Docker image checks
   # or directly: uv run validate
   ```

3. **Test locally with Docker**:
   ```bash
   just test-local
   # or directly: uv run test-local
   # Clean up test environment: just test-clean
   ```

4. **Configure for production**:
   ```bash
   just setup
   # Edit ansible/inventories/production.yml with your VPS IP and domain
   ```

5. **Deploy to VPS**:
   ```bash
   just check             # Check Ansible syntax first
   just dry-run           # Test deployment without changes
   just deploy            # Deploy to production
   # or with verbose output: just deploy-verbose
   ```

## Usage Commands

### Testing & Validation Commands
```bash
just validate           # Fast validation (skips Docker pulls)
just validate-full      # Full validation with Docker image checks
just test-local         # Test configuration locally with Docker
just test-clean         # Clean up local test environment
```

### Deployment Commands
```bash
just setup              # Create production inventory from template
just check              # Check Ansible syntax
just dry-run            # Test deployment without making changes
just deploy             # Deploy all services to VPS
just deploy-verbose     # Deploy with verbose Ansible output
```

### Management & Monitoring Commands
```bash
just ping               # Test VPS connectivity
just health-check       # Run comprehensive health checks
just restart <service>  # Restart specific service (e.g., grafana, prometheus)
just logs <service>     # View logs for specific service
just ssh                # Quick VPS connection test
just clean              # Clean temporary files
```

## Services Access

After deployment, services will be available at:

**With domain** (configured via Caddy reverse proxy):
- Grafana: `https://grafana.yourdomain.com`
- Prometheus: `https://prometheus.yourdomain.com` 
- Loki: `https://loki.yourdomain.com`

**Direct access** (using server IP and ports):
- Grafana: `https://YOUR_VPS_IP:3000` (default port in group_vars)
- Prometheus: `https://YOUR_VPS_IP:9090`
- Loki: `https://YOUR_VPS_IP:3100`
- Node Exporter: `http://YOUR_VPS_IP:9100`

**Default credentials:**
- Grafana: `admin/admin` (change on first login)

## Python Scripts & Automation

The project includes several Python scripts for automation:

- **validate.py**: Pre-deployment validation (syntax, prerequisites, Docker images)
- **test_local.py**: Local Docker-based testing with full deployment simulation  
- **deploy.py**: Ansible deployment wrapper with syntax checking and dry-run capabilities
- **health_check.py**: Infrastructure health checks for connectivity, resources, and services

All scripts support:
- Colored output for better visibility
- Detailed error reporting and debugging
- Can be run via `uv run <script-name>` or corresponding `just` commands

## Customization

### Adding Your Applications
Edit `ansible/roles/caddy/templates/Caddyfile.j2` to add reverse proxy rules for your applications.

### Modifying Service Configuration
- **Global variables**: Edit `ansible/group_vars/all.yml`
- **Host-specific settings**: Create files in `ansible/host_vars/`
- **Service templates**: Modify templates in each role's `templates/` directory

### Local Testing Environment
The `docker/test-environment/` provides a systemd-enabled container for testing Ansible playbooks locally before production deployment.