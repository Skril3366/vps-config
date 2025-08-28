# Deployment Guide

This comprehensive guide covers deploying the VPS configuration from initial setup through production deployment and ongoing management.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Configuration](#configuration)
- [Local Testing](#local-testing)
- [Production Deployment](#production-deployment)
- [Post-Deployment Verification](#post-deployment-verification)
- [Ongoing Management](#ongoing-management)
- [Rollback Procedures](#rollback-procedures)

## Prerequisites

### Local Environment
Ensure these tools are installed on your local machine:

```bash
# macOS (using Homebrew)
brew install just uv docker

# Ubuntu/Debian
curl -LsSf https://astral.sh/uv/install.sh | sh
snap install docker
wget -qO - https://github.com/casey/just/releases/latest/download/just-*.tar.gz | tar xz just

# Verify installations
just --version
uv --version
docker --version
```

### VPS Requirements
Your target VPS should meet these minimum requirements:

- **OS**: Ubuntu 20.04 LTS or newer
- **RAM**: 2GB minimum (4GB recommended)
- **Storage**: 20GB minimum (40GB recommended)
- **Network**: Public IP address with domains pointing to it
- **Access**: SSH key-based authentication with sudo privileges

### DNS Configuration
Before deployment, configure your DNS records:

```
Type    Name                    Value               TTL
A       yourdomain.com          YOUR_VPS_IP         300
A       auth.yourdomain.com     YOUR_VPS_IP         300
A       grafana.yourdomain.com  YOUR_VPS_IP         300
A       prometheus.yourdomain.com YOUR_VPS_IP       300
A       loki.yourdomain.com     YOUR_VPS_IP         300
```

## Initial Setup

### 1. Clone and Initialize Project

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd vps-config

# Install Python dependencies
uv sync

# Verify setup
just validate
```

### 2. Create Production Inventory

```bash
# Copy template and customize
just setup

# Edit the production inventory file
vim ansible/inventories/production.yml
```

Configure your production inventory (`ansible/inventories/production.yml`):

```yaml
---
all:
  hosts:
    vps:
      ansible_host: YOUR_VPS_IP_ADDRESS
      ansible_user: YOUR_SSH_USER
      ansible_ssh_private_key_file: ~/.ssh/your_private_key
      ansible_become: yes
      ansible_become_method: sudo
  
  vars:
    # Your domain configuration
    domain_name: "yourdomain.com"
    
    # Email for Let's Encrypt certificates
    letsencrypt_email: "you@yourdomain.com"
    
    # SSH configuration
    ssh_port: 22
    
    # Optional: Custom service ports
    # authelia_port: 9091
    # grafana_port: 3000
    # prometheus_port: 9090
    # loki_port: 3100
```

### 3. Test VPS Connectivity

```bash
# Test basic SSH connectivity
just ping

# Should return something like:
# vps | SUCCESS => {
#     "changed": false,
#     "ping": "pong"
# }
```

## Configuration

### 1. Configure Authelia Secrets (REQUIRED)

Authelia requires secure secrets for proper operation. **This step is mandatory before deployment.**

#### Create Environment File
```bash
# Create the environment directory and file
mkdir -p ansible/inventories/production
cp ansible/inventories/production/.env.example ansible/inventories/production/.env
```

#### Generate Secure Secrets
Generate three secure random secrets (minimum 32 characters each):

```bash
# Generate JWT secret (for token signing)
JWT_SECRET=$(openssl rand -base64 32)
echo "JWT Secret: $JWT_SECRET"

# Generate session secret (for session encryption)
SESSION_SECRET=$(openssl rand -base64 32)
echo "Session Secret: $SESSION_SECRET"

# Generate storage encryption key (for database encryption)
STORAGE_KEY=$(openssl rand -base64 32)
echo "Storage Key: $STORAGE_KEY"
```

#### Generate Admin Password Hash
Create a secure password hash for your admin user:

```bash
# Replace 'your-secure-password' with your actual password
just authelia-hash 'your-secure-password'

# Or use the full Docker command:
docker run --rm authelia/authelia:latest authelia crypto hash generate argon2 --password 'your-secure-password'

# Example output:
# $argon2id$v=19$m=65536,t=3,p=4$abcdefghijklmnopqrstuvwxyz123456$longhashstringhere
```

#### Edit Environment File
Edit `ansible/inventories/production/.env`:

```bash
# Authentication secrets (use generated values from above)
AUTHELIA_JWT_SECRET="your_generated_jwt_secret"
AUTHELIA_SESSION_SECRET="your_generated_session_secret"
AUTHELIA_STORAGE_ENCRYPTION_KEY="your_generated_storage_key"

# Admin user configuration
AUTHELIA_ADMIN_USER=admin
AUTHELIA_ADMIN_DISPLAYNAME=Administrator
AUTHELIA_ADMIN_EMAIL=admin@yourdomain.com

# Admin password hash (NO QUOTES around the hash value)
AUTHELIA_ADMIN_PASSWORD_HASH=$argon2id$v=19$m=65536,t=3,p=4$abcdefghijklmnopqrstuvwxyz123456$longhashstringhere

# Email configuration (optional, for password reset)
AUTHELIA_SMTP_HOST=smtp.gmail.com
AUTHELIA_SMTP_PORT=587
AUTHELIA_SMTP_USERNAME=your-email@gmail.com
AUTHELIA_SMTP_PASSWORD=your-app-password
AUTHELIA_SENDER=noreply@yourdomain.com
```

**Important Notes**:
- Secrets should be enclosed in **double quotes**
- Password hash should **NOT** have quotes around it
- Keep this file secure and never commit it to version control

### 2. Customize Service Configuration (Optional)

#### Global Variables
Edit `ansible/group_vars/all.yml` to customize global settings:

```yaml
# System configuration
system_timezone: "America/New_York"  # Change timezone

# Service ports (if different from defaults)
authelia_port: 9091
grafana_port: 3000
prometheus_port: 9090
loki_port: 3100

# Docker image versions (pin to specific versions if needed)
caddy_image: "caddy:2.7-alpine"
authelia_image: "authelia/authelia:4.38"
prometheus_image: "prom/prometheus:v2.45.0"

# Monitoring retention
prometheus_retention_time: "30d"  # Keep metrics for 30 days

# Security settings
fail2ban_enabled: true
unattended_upgrades_enabled: true
automatic_reboot: false  # Set to true for automatic security reboots
```

#### Service-Specific Configuration
Customize individual services by editing their respective template files:

- **Caddy**: `ansible/roles/caddy/templates/Caddyfile.j2`
- **Prometheus**: `ansible/roles/monitoring/templates/prometheus.yml.j2`
- **Grafana**: `ansible/roles/monitoring/templates/datasources.yml.j2`

## Local Testing

Before deploying to production, test your configuration locally using Docker:

### 1. Run Full Validation
```bash
# Quick validation (skips Docker image pulls)
just validate

# Full validation (includes Docker image availability checks)
just validate-full
```

### 2. Test Locally with Docker
```bash
# Start local test environment
just test-local

# This will:
# 1. Build a test container with systemd
# 2. Apply all Ansible configurations
# 3. Start all services
# 4. Run health checks
```

### 3. Access Local Services
During local testing, services are available on different ports:
- SSH to test container: `ssh -p 2222 root@localhost`
- Caddy (HTTP): `http://localhost:8080`
- Grafana: `http://localhost:3001` (admin/admin)
- Prometheus: `http://localhost:9091`

### 4. Clean Up Test Environment
```bash
# Remove test containers and volumes
just test-clean
```

## Production Deployment

### 1. Pre-Deployment Checks

Run syntax and connectivity checks:

```bash
# Check Ansible playbook syntax
just check

# Test deployment without making changes (dry-run)
just dry-run

# The dry-run will show you exactly what changes will be made
```

### 2. Deploy to Production

Deploy all services with a single command:

```bash
# Standard deployment
just deploy

# Or with verbose output for troubleshooting
just deploy-verbose
```

**The deployment will:**
1. Update system packages and install dependencies
2. Configure SSH hardening and firewall rules
3. Install and configure Docker
4. Deploy Authelia authentication service
5. Set up Caddy reverse proxy with automatic HTTPS
6. Deploy monitoring stack (Prometheus, Grafana, Loki)
7. Configure all service integrations
8. Run health checks to verify deployment

### 3. Deployment Process Breakdown

The deployment follows this sequence:

#### Phase 1: System Preparation (common role)
- Update package cache
- Install essential packages
- Create service directories with proper permissions
- Configure system timezone

#### Phase 2: Security Hardening (security role)
- Configure SSH with key-based authentication
- Set up UFW firewall with restrictive rules
- Install and configure fail2ban
- Enable unattended security updates

#### Phase 3: Docker Setup (docker role)
- Add Docker APT repository
- Install Docker Engine and Docker Compose
- Configure Docker daemon
- Start and enable Docker service

#### Phase 4: Authentication (authelia role)
- Create Authelia configuration from templates
- Deploy Authelia and Redis containers
- Configure user database and access control

#### Phase 5: Reverse Proxy (caddy role)
- Generate Caddyfile with domain configuration
- Deploy Caddy container with Let's Encrypt integration
- Configure forward authentication with Authelia

#### Phase 6: Monitoring (monitoring role)
- Deploy Prometheus with system targets
- Set up Grafana with pre-configured dashboards
- Configure Loki for log aggregation
- Deploy Promtail for log collection
- Set up Node Exporter for system metrics

## Post-Deployment Verification

### 1. Run Health Checks

```bash
# Comprehensive health check
just health-check

# This verifies:
# - VPS connectivity and resources
# - Service container status
# - HTTP endpoint availability
# - SSL certificate validity
# - Authentication flow
```

### 2. Manual Service Verification

#### Check Service Status
```bash
# View all running containers
just logs docker ps

# Check specific service logs
just logs authelia
just logs caddy
just logs prometheus
just logs grafana
```

#### Test Service Endpoints

1. **Authentication Portal**:
   - Visit `https://auth.yourdomain.com`
   - Login with your admin credentials
   - Complete 2FA setup with your authenticator app

2. **Grafana Dashboard**:
   - Visit `https://grafana.yourdomain.com`
   - Should redirect to auth portal if not logged in
   - After authentication, should show Grafana interface

3. **Prometheus Metrics**:
   - Visit `https://prometheus.yourdomain.com`
   - Check Status → Targets to see all metric endpoints

4. **SSL Certificates**:
   ```bash
   # Check certificate validity
   curl -sI https://yourdomain.com | grep -i strict-transport
   openssl s_client -connect yourdomain.com:443 -servername yourdomain.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
   ```

### 3. Troubleshooting Failed Deployments

If deployment fails, check:

```bash
# Check Ansible logs for errors
just deploy-verbose

# Check specific service issues
just logs <service-name>

# Verify DNS resolution
nslookup auth.yourdomain.com
nslookup grafana.yourdomain.com

# Check firewall rules
just ssh "sudo ufw status verbose"

# Verify Docker network connectivity
just ssh "docker network ls"
just ssh "docker network inspect vps-config_default"
```

## Ongoing Management

### Regular Maintenance Commands

```bash
# Check system health
just health-check

# Restart specific services
just restart grafana
just restart prometheus
just restart authelia

# View recent service logs
just logs caddy
just logs authelia --tail 100

# Update and redeploy specific components
just deploy-authelia           # Update only Authelia
just update-caddy             # Update only Caddy configuration

# Clean up old Docker images and containers
just ssh "docker system prune -f"
```

### Monitoring and Alerting

After deployment, monitor your system through:

1. **Grafana Dashboards**:
   - System Overview: CPU, memory, disk usage
   - Docker Overview: Container metrics
   - Logs Overview: Application and system logs

2. **Prometheus Alerts** (configured in `prometheus.yml`):
   - High CPU usage (>80% for 5 minutes)
   - High memory usage (>90% for 5 minutes)
   - Disk space low (<10% remaining)
   - Service down detection

3. **Log Analysis through Loki**:
   - Authentication failures
   - System errors and warnings
   - Service restart events

### Security Maintenance

```bash
# Check for failed authentication attempts
just logs authelia | grep -i "failed\|error"

# View fail2ban status
just ssh "sudo fail2ban-client status"
just ssh "sudo fail2ban-client status sshd"

# Check system updates
just ssh "apt list --upgradable"

# Reset Authelia bans (if locked out)
just reset-authelia-bans
```

## Rollback Procedures

### Service-Level Rollback

If a specific service deployment fails:

```bash
# Rollback to previous container version
just ssh "docker stop <service-name>"
just ssh "docker rm <service-name>"

# Redeploy with previous configuration
git checkout HEAD~1 -- ansible/roles/<service-name>/
just deploy
```

### Full System Rollback

For complete system restoration:

1. **Stop all services**:
   ```bash
   just ssh "docker stop \$(docker ps -q)"
   ```

2. **Restore from backups** (if configured):
   ```bash
   # Restore configuration files
   just ssh "sudo cp -r /backup/opt/* /opt/"
   
   # Restart services
   just deploy
   ```

3. **Emergency access**:
   - SSH is always available (not containerized)
   - Direct IP access to services on their native ports
   - Caddy bypass using IP:port combinations

### Configuration Rollback

To rollback configuration changes:

```bash
# Reset to previous git state
git log --oneline -10              # Find previous commit
git checkout <commit-hash> -- ansible/

# Redeploy with previous configuration
just deploy

# Or rollback specific service
git checkout <commit-hash> -- ansible/roles/<service>/
just deploy
```

### Emergency Recovery

In case of complete system failure:

1. **Direct SSH Access**: Always available on configured SSH port
2. **Stop problematic services**: `docker stop <container>`
3. **Access logs**: `/opt/logs/` for all service logs
4. **Manual service start**: Use docker commands directly
5. **Firewall bypass**: Temporarily disable UFW if needed

## Best Practices

### Deployment Best Practices

1. **Always test locally first**: Use `just test-local`
2. **Use dry-run for production**: Run `just dry-run` before deployment
3. **Monitor during deployment**: Watch service logs during deployment
4. **Verify after deployment**: Run health checks immediately after
5. **Keep backups**: Regular configuration and data backups

### Configuration Management

1. **Version control everything**: All configuration in Git
2. **Use separate branches**: Feature branches for major changes
3. **Document changes**: Clear commit messages and documentation
4. **Test incrementally**: Small, testable changes
5. **Keep secrets secure**: Never commit secrets to version control

### Security Considerations

1. **Regular updates**: Keep system and containers updated
2. **Monitor logs**: Regular log review for security events
3. **Access control**: Limit SSH access, use strong passwords
4. **Certificate monitoring**: Monitor SSL certificate expiration
5. **Backup verification**: Regular backup testing and verification