# Personal VPS Configuration

Simple Ansible-based configuration for a personal VPS with monitoring and reverse proxy.

## What's Included

- **Caddy**: Reverse proxy with automatic HTTPS
- **Docker**: Container runtime for all services
- **Authelia**: Authentication and authorization service with 2FA support
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
│   │   ├── authelia/   # Authentication service with 2FA and Redis session storage
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

5. **Setup Authelia secrets** (see [Authelia Setup](#authelia-setup) section below)

6. **Deploy to VPS**:
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

### Authelia-Specific Commands
```bash
just deploy-authelia        # Deploy only Authelia service
just reset-authelia-bans    # Clear user bans and reset regulation database
just authelia-hash <pass>   # Generate password hash for Authelia users
```

## Authelia Setup

Authelia provides authentication and authorization for all services with 2FA support. **This is required before first deployment.**

### 1. Create Environment File

Copy the template and create your environment file:
```bash
mkdir -p ansible/inventories/production
cp .env.example ansible/inventories/production/.env
```

### 2. Generate Secure Secrets

Generate three secure secrets (minimum 32 characters each):
```bash
# Generate JWT secret
openssl rand -base64 32

# Generate session secret
openssl rand -base64 32

# Generate storage encryption key
openssl rand -base64 32
```

### 3. Generate Admin Password Hash

Create a password hash for your admin user using the **correct command**:
```bash
# Replace 'yourpassword' with your desired password
docker run --rm authelia/authelia:latest authelia crypto hash generate argon2 --password 'yourpassword'

# Or use the built-in just command
just authelia-hash 'yourpassword'
```

### 4. Edit Environment File

Edit `ansible/inventories/production/.env` and update all values:
```bash
# Required secrets (use values from step 2)
AUTHELIA_JWT_SECRET="your_generated_jwt_secret"
AUTHELIA_SESSION_SECRET="your_generated_session_secret" 
AUTHELIA_STORAGE_ENCRYPTION_KEY="your_generated_storage_key"

# Admin user configuration
AUTHELIA_ADMIN_USER=admin
AUTHELIA_ADMIN_DISPLAYNAME=Administrator
AUTHELIA_ADMIN_EMAIL=admin@yourdomain.com

# Admin Password Hash - NO QUOTES around the hash value
AUTHELIA_ADMIN_PASSWORD_HASH=$argon2id$v=19$m=65536,t=3,p=4$HASH_HERE
```

**Important formatting notes:**
- Secrets should be in **double quotes**
- Password hash should **NOT** have quotes around it
- Use the exact hash output from the generation command

### 5. Access After Deployment

1. **Access auth portal**: `https://auth.yourdomain.com`
2. **Login** with your admin credentials
3. **Setup 2FA** using the QR code with your authenticator app
4. **Test access** to protected services

### Troubleshooting Common Issues

**"Incorrect password" errors:**
1. **Check username format**: Use `admin` (not your email address)
2. **Verify password hash**: Regenerate using `just authelia-hash 'yourpassword'`  
3. **User banned**: Run `just reset-authelia-bans` to clear temporary bans
4. **Check logs**: Use `just logs authelia` to see detailed debug information

**Password hash generation:**
- **Correct command**: `docker run --rm authelia/authelia:latest authelia crypto hash generate argon2 --password 'yourpassword'`
- **Old deprecated command**: `authelia hash-password` (don't use this)

**Regulation system:**
- Max retries: 10 failed attempts allowed
- Ban duration: 5 minutes (very lenient)
- Reset bans: `just reset-authelia-bans`

### Security Notes

- Environment file has restricted permissions (0600) on the server
- All secrets are excluded from version control via `.gitignore`
- Services are protected by forward authentication through Authelia
- 2FA is required for all user accounts
- Regulation system prevents brute force attacks with reasonable limits

## Services Access

After deployment, services will be available at:

**Authentication Portal**:
- **Authelia**: `https://auth.yourdomain.com`

**Protected Services** (require authentication via Authelia):
- **Grafana**: `https://grafana.yourdomain.com`
- **Prometheus**: `https://prometheus.yourdomain.com`
- **Loki**: `https://loki.yourdomain.com`

**Monitoring Services**:
- **Node Exporter**: `http://YOUR_VPS_IP:9100` (direct access)

**Direct access** (bypasses authentication, for troubleshooting):
- Available on configured ports using server IP
- Not recommended for production use

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
