# Personal VPS Configuration

A complete Ansible-based solution for deploying and managing a personal VPS with monitoring, authentication, and security hardening. This project sets up a production-ready infrastructure with automatic HTTPS, comprehensive monitoring, and secure authentication with 2FA.

## What's Included

- **🔒 Authelia**: Authentication and authorization service with 2FA support
- **🌐 Caddy**: Reverse proxy with automatic HTTPS and Let's Encrypt certificates
- **🐳 Docker**: Container runtime for all services with proper orchestration
- **📊 Monitoring Stack**: Prometheus, Grafana, Loki, and Promtail for observability
- **🛡️ Security**: SSH hardening, firewall rules, fail2ban protection, and unattended upgrades
- **🧪 Local Testing**: Docker-based testing environment for safe deployments

## 📚 Documentation

This project includes comprehensive documentation organized into specialized guides:

### Getting Started
- **[Quick Start Guide](docs/quick-start.md)** - Get up and running in minutes
- **[Installation Guide](docs/installation.md)** - Detailed setup instructions
- **[Configuration Guide](docs/configuration.md)** - Complete configuration reference

### Architecture & Design
- **[Architecture Overview](docs/architecture.md)** - System design and component relationships
- **[Service Documentation](docs/services.md)** - Detailed service configurations and endpoints

### Operations & Management
- **[Deployment Guide](docs/deployment.md)** - Step-by-step deployment procedures
- **[Management Guide](docs/management.md)** - Day-to-day operational tasks
- **[Monitoring Guide](docs/monitoring.md)** - Observability and alerting setup

### Reference & Troubleshooting
- **[Command Reference](docs/commands.md)** - Complete command documentation
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common issues and solutions
- **[Security Guide](docs/security.md)** - Security best practices and hardening

### Advanced Topics
- **[Development Guide](docs/development.md)** - Local testing and contribution guidelines
- **[Customization Guide](docs/customization.md)** - Extending and modifying the setup

## 🚀 Quick Start

### Prerequisites
- **just**: Task runner (`brew install just` on macOS)
- **uv**: Python package manager (`brew install uv`)
- **Docker**: For local testing
- **SSH access** to your VPS with sudo privileges

### Basic Setup
```bash
# 1. Install dependencies
uv sync

# 2. Validate configuration
just validate

# 3. Test locally
just test-local

# 4. Setup production inventory
just setup
# Edit ansible/inventories/production.yml with your VPS details

# 5. Configure Authelia secrets (REQUIRED)
# See docs/configuration.md for detailed steps

# 6. Deploy
just deploy
```

## 📖 Key Documentation Links

| Task | Documentation |
|------|---------------|
| First-time setup | [Installation Guide](docs/installation.md) |
| Configure services | [Configuration Guide](docs/configuration.md) |
| Deploy to production | [Deployment Guide](docs/deployment.md) |
| Monitor your VPS | [Monitoring Guide](docs/monitoring.md) |
| Troubleshoot issues | [Troubleshooting Guide](docs/troubleshooting.md) |
| Add custom services | [Customization Guide](docs/customization.md) |

## 🎯 Common Commands

```bash
# Testing & Validation
just validate           # Quick validation
just test-local         # Test locally with Docker

# Deployment
just deploy             # Deploy all services
just deploy-authelia    # Deploy only authentication

# Management  
just health-check       # Check system health
just restart grafana    # Restart specific service
just logs prometheus    # View service logs
```

## 🌐 Service Access

After deployment, services are available at:

- **🔐 Authelia (Auth Portal)**: `https://auth.yourdomain.com`
- **📊 Grafana (Dashboards)**: `https://grafana.yourdomain.com`
- **🔍 Prometheus (Metrics)**: `https://prometheus.yourdomain.com`
- **📝 Loki (Logs)**: `https://loki.yourdomain.com`

All services except Authelia require authentication through the auth portal.

## 🏗️ Repository Structure

```
vps-config/
├── docs/                    # 📚 Complete documentation
├── ansible/                 # 🎭 Ansible automation
│   ├── roles/              # Service-specific configurations
│   ├── playbooks/          # Deployment orchestration
│   ├── inventories/        # Environment configurations
│   └── group_vars/         # Global variables
├── docker/                 # 🐳 Docker configurations
│   ├── compose/           # Service definitions
│   └── test-environment/  # Local testing setup
├── scripts/                # 🐍 Python automation tools
├── justfile               # 🔧 Task automation
└── pyproject.toml         # 📦 Project dependencies
```

## 💡 Key Features

- **Zero-downtime deployments** with health checks
- **Automatic HTTPS** with Let's Encrypt certificates
- **2FA authentication** for all services
- **Comprehensive monitoring** with alerting
- **Security hardening** by default
- **Local testing environment** for safe changes
- **Automated backups** and maintenance
- **Extensive documentation** and troubleshooting guides

## 🤝 Contributing

See the [Development Guide](docs/development.md) for information on:
- Local development setup
- Testing procedures
- Contributing guidelines
- Code style and conventions

## 📄 License

This project is open source and available under the MIT License.