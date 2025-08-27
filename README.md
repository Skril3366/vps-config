# Personal VPS Configuration

Simple Ansible-based configuration for a personal VPS with monitoring and reverse proxy.

## What's Included

- **Caddy**: Reverse proxy with automatic HTTPS
- **Docker**: Container runtime for all services
- **Prometheus + Node Exporter**: System metrics collection
- **Grafana**: Monitoring dashboard
- **Loki + Promtail**: Log aggregation and collection

## Repository Structure

```
├── ansible/
│   ├── roles/
│   │   ├── common/     # Basic system setup
│   │   ├── security/   # Security hardening
│   │   ├── docker/     # Docker installation
│   │   ├── caddy/      # Reverse proxy setup
│   │   └── monitoring/ # Prometheus, Grafana, Loki
│   ├── playbooks/
│   │   └── site.yml    # Main playbook
│   └── inventories/
│       └── hosts.yml   # Server inventory template
└── justfile           # Task automation
```

## Quick Start

### Prerequisites

- **just**: Task runner (`brew install just`)
- **uv**: Fast Python package manager (`brew install uv`)
- **Docker**: For local testing
- **SSH access** to your VPS

### Setup & Testing

1. **Initialize project and install dependencies**:
   ```bash
   uv sync
   ```

2. **Validate configuration**:
   ```bash
   just validate
   # or directly: uv run validate
   ```

3. **Test locally with Docker**:
   ```bash
   just test-local
   # or directly: uv run test-local
   ```

4. **Configure for production**:
   ```bash
   just setup
   # Edit ansible/inventories/production.yml with your VPS IP and domain
   ```

5. **Deploy to VPS**:
   ```bash
   just deploy
   ```

## Usage Commands

### Testing Commands
```bash
just validate           # Run all validation tests
just test-local         # Test configuration locally with Docker
just test-clean         # Clean up local test environment
```

### Deployment Commands
```bash
just setup              # Create production inventory
just check              # Check Ansible syntax
just dry-run            # Test deployment without changes
just deploy             # Deploy all services
```

### Management Commands
```bash
just ping               # Test VPS connectivity
just health-check       # Show running containers
just restart grafana    # Restart specific service
just logs prometheus    # View service logs
```

## Services Access

After deployment, services will be available at:

**With domain**:
- Grafana: `https://grafana.amenocturne.space`
- Prometheus: `https://prometheus.amenocturne.space` 
- Loki: `https://loki.amenocturne.space`

**Without domain** (using IP):
- Grafana: `https://YOUR_IP:3001`
- Prometheus: `https://YOUR_IP:9091`
- Loki: `https://YOUR_IP:3101`

Default Grafana login: `admin/admin`

## Adding Your Apps

Edit `ansible/roles/caddy/templates/Caddyfile.j2` to add reverse proxy rules for your applications.