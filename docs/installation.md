# Installation Guide

This comprehensive guide covers the complete installation process for the VPS configuration, from initial setup through production deployment.

## Table of Contents
- [System Requirements](#system-requirements)
- [Local Environment Setup](#local-environment-setup)
- [VPS Preparation](#vps-preparation)
- [Project Installation](#project-installation)
- [Configuration Setup](#configuration-setup)
- [Deployment Process](#deployment-process)
- [Post-Installation Verification](#post-installation-verification)
- [Optional Configurations](#optional-configurations)

## System Requirements

### Local Machine Requirements

**Operating System Support**:
- macOS 10.15+ (recommended)
- Ubuntu 18.04+ / Debian 10+
- Windows 10+ (with WSL2)

**Required Tools**:
- **Python 3.8+**: For running automation scripts
- **Docker**: For local testing
- **Git**: For version control
- **SSH client**: For VPS access

**Recommended Specifications**:
- 4GB RAM minimum
- 10GB free disk space
- Reliable internet connection

### VPS Requirements

**Minimum Specifications**:
- **OS**: Ubuntu 20.04 LTS or newer
- **RAM**: 2GB (4GB recommended for heavy monitoring)
- **Storage**: 20GB SSD (40GB recommended)
- **Network**: Public IP address
- **Access**: SSH key-based authentication with sudo privileges

**Recommended VPS Providers**:
- DigitalOcean (Droplet)
- Linode (Nanode/Shared CPU)
- Vultr (Regular Performance)
- AWS EC2 (t3.small or larger)
- Hetzner Cloud (CX21 or larger)

**Network Requirements**:
- Ports 22 (SSH), 80 (HTTP), 443 (HTTPS) must be accessible
- Domain name with ability to modify DNS records
- Optional: Static IP (recommended for production)

## Local Environment Setup

### Install Package Managers

#### macOS (using Homebrew)
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required tools
brew install just uv docker git

# Start Docker
open -a Docker
```

#### Ubuntu/Debian
```bash
# Update package index
sudo apt update

# Install essential tools
sudo apt install -y curl wget git python3 python3-pip

# Install just (task runner)
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/bin
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Log out and back in for Docker group membership
```

#### Windows (WSL2)
```powershell
# Install WSL2 if not already installed
wsl --install -d Ubuntu

# Then follow Ubuntu installation steps above
```

### Verify Local Installation
```bash
# Check tool versions
just --version        # Should show just version
uv --version          # Should show uv version  
docker --version      # Should show Docker version
python3 --version     # Should show Python 3.8+
git --version         # Should show Git version

# Test Docker
docker run hello-world
```

## VPS Preparation

### Initial VPS Setup

#### Create VPS Instance
1. **Choose provider** (DigitalOcean, Linode, etc.)
2. **Select OS**: Ubuntu 20.04 LTS (or newer)
3. **Choose size**: Minimum 2GB RAM, 20GB storage
4. **Add SSH key**: Upload your public SSH key
5. **Create instance** and note the public IP address

#### Initial SSH Configuration
```bash
# Test SSH connection
ssh root@YOUR_VPS_IP

# Create non-root user (if not already done)
adduser ubuntu
usermod -aG sudo ubuntu

# Copy SSH keys to new user
mkdir -p /home/ubuntu/.ssh
cp /root/.ssh/authorized_keys /home/ubuntu/.ssh/
chown -R ubuntu:ubuntu /home/ubuntu/.ssh
chmod 700 /home/ubuntu/.ssh
chmod 600 /home/ubuntu/.ssh/authorized_keys

# Test connection with new user
ssh ubuntu@YOUR_VPS_IP
```

#### Basic VPS Security (Optional - will be done by Ansible)
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git htop vim unzip

# Configure timezone (optional)
sudo timedatectl set-timezone UTC
```

### Domain and DNS Setup

#### Domain Requirements
You need a domain name with DNS management access. The following subdomains will be used:
- `yourdomain.com` (main domain)
- `auth.yourdomain.com` (authentication portal)
- `grafana.yourdomain.com` (monitoring dashboards)
- `prometheus.yourdomain.com` (metrics collection)
- `loki.yourdomain.com` (log aggregation)

#### Configure DNS Records
Add these DNS records pointing to your VPS IP:

```
Type    Name                    Value           TTL
A       @                       YOUR_VPS_IP     300
A       auth                    YOUR_VPS_IP     300
A       grafana                 YOUR_VPS_IP     300
A       prometheus              YOUR_VPS_IP     300
A       loki                    YOUR_VPS_IP     300
```

**DNS Provider Examples**:

**Cloudflare**:
1. Login to Cloudflare dashboard
2. Select your domain
3. Go to DNS management
4. Add A records for each subdomain

**Namecheap**:
1. Login to Namecheap account
2. Go to Domain List → Manage
3. Advanced DNS → Add new records

**DigitalOcean DNS**:
1. Create DNS zone in DigitalOcean
2. Add A records for subdomains
3. Update nameservers at domain registrar

#### Verify DNS Propagation
```bash
# Check DNS resolution
nslookup auth.yourdomain.com
dig A grafana.yourdomain.com

# Check from multiple locations
# Use online tools like whatsmydns.net
```

## Project Installation

### Clone Repository
```bash
# Clone the project
git clone <repository-url>
cd vps-config

# Verify project structure
ls -la
# Should show: ansible/, docs/, scripts/, justfile, pyproject.toml, etc.
```

### Install Python Dependencies
```bash
# Install project dependencies using uv
uv sync

# Verify installation
uv run --help
uv run validate --help
```

### Initial Validation
```bash
# Run quick validation (skips Docker image checks)
just validate

# Expected output: All validation checks should pass
# If there are issues, they will be clearly indicated
```

### Local Testing Setup (Optional but Recommended)
```bash
# Test the configuration locally with Docker
just test-local

# This will:
# 1. Build a test environment
# 2. Deploy all services locally
# 3. Run health checks
# 4. Report any configuration issues

# Clean up after testing
just test-clean
```

## Configuration Setup

### Production Inventory Configuration

#### Create Production Inventory
```bash
# Create production inventory from template
just setup

# This creates: ansible/inventories/production.yml
```

#### Configure VPS Details
Edit `ansible/inventories/production.yml`:

```yaml
---
all:
  hosts:
    vps:
      # VPS connection details
      ansible_host: "YOUR_VPS_IP_ADDRESS"
      ansible_user: "ubuntu"  # or your SSH username
      ansible_ssh_private_key_file: "~/.ssh/id_rsa"  # path to your SSH key
      ansible_become: yes
      ansible_become_method: sudo
      
      # Python interpreter (usually auto-detected)
      ansible_python_interpreter: "/usr/bin/python3"
  
  vars:
    # Domain configuration (REQUIRED)
    domain_name: "yourdomain.com"
    letsencrypt_email: "admin@yourdomain.com"
    
    # SSH configuration (optional customization)
    ssh_port: 22  # Change this for additional security
    
    # Optional: Override default service ports
    # authelia_port: 9091
    # grafana_port: 3000
    # prometheus_port: 9090
    # loki_port: 3100
    
    # Optional: Specify Docker image versions
    # caddy_image: "caddy:2.7-alpine"
    # authelia_image: "authelia/authelia:4.38"
    # prometheus_image: "prom/prometheus:v2.45.0"
```

#### Test VPS Connectivity
```bash
# Test SSH connection through Ansible
just ping

# Expected output:
# vps | SUCCESS => {
#     "changed": false,
#     "ping": "pong"
# }
```

### Authelia Authentication Configuration

**⚠️ This step is critical and must be completed before deployment!**

#### Generate Secure Secrets
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

# IMPORTANT: Save these values - you'll need them in the next step!
```

#### Generate Admin Password Hash
```bash
# Replace 'your-secure-password' with your desired admin password
just authelia-hash 'your-secure-password'

# Alternative method using Docker directly:
docker run --rm authelia/authelia:latest authelia crypto hash generate argon2 --password 'your-secure-password'

# Example output (copy the entire hash):
# $argon2id$v=19$m=65536,t=3,p=4$abcdefghijklmnopqrstuvwxyz123456$longhashstring...
```

#### Create Environment File
```bash
# Create the environment file directory
mkdir -p ansible/inventories/production

# Create environment file (if it doesn't exist)
touch ansible/inventories/production/.env

# Edit the environment file
vim ansible/inventories/production/.env
```

Configure the environment file with your values:
```bash
# Authentication secrets (use the values generated above)
# IMPORTANT: Keep the double quotes around secrets
AUTHELIA_JWT_SECRET="your_generated_jwt_secret_here"
AUTHELIA_SESSION_SECRET="your_generated_session_secret_here"  
AUTHELIA_STORAGE_ENCRYPTION_KEY="your_generated_storage_key_here"

# Admin user configuration
AUTHELIA_ADMIN_USER=admin
AUTHELIA_ADMIN_DISPLAYNAME=Administrator
AUTHELIA_ADMIN_EMAIL=admin@yourdomain.com

# Admin password hash
# IMPORTANT: NO QUOTES around the password hash!
AUTHELIA_ADMIN_PASSWORD_HASH=$argon2id$v=19$m=65536,t=3,p=4$your_hash_here

# Optional: SMTP configuration for password reset emails
# AUTHELIA_SMTP_HOST=smtp.gmail.com
# AUTHELIA_SMTP_PORT=587
# AUTHELIA_SMTP_USERNAME=your-email@gmail.com
# AUTHELIA_SMTP_PASSWORD=your-app-specific-password
# AUTHELIA_SENDER=noreply@yourdomain.com
```

**Important Notes**:
- Secrets must be enclosed in **double quotes**
- Password hash must **NOT** have quotes around it
- Use strong, unique passwords
- Never commit this file to version control (it's in .gitignore)

#### Verify Configuration
```bash
# Check that environment file has correct permissions and content
ls -la ansible/inventories/production/.env
# Should show: -rw------- (600 permissions)

# Verify no syntax errors in inventory
just check

# Run configuration validation
just validate-full
```

## Deployment Process

### Pre-Deployment Validation

#### Comprehensive Validation
```bash
# Run full validation including Docker image checks
just validate-full

# This checks:
# - Ansible syntax and configuration
# - Required tools and dependencies  
# - Docker image availability
# - SSH connectivity to VPS
# - Environment file completeness
```

#### Ansible Syntax Check
```bash
# Verify Ansible playbook syntax
just check

# Expected output: "playbook: ansible/playbooks/site.yml"
# Any syntax errors will be clearly displayed
```

#### Dry Run Deployment
```bash
# Test deployment without making changes
just dry-run

# This shows exactly what changes will be made:
# - Package installations
# - Configuration file updates
# - Service deployments
# - File permission changes
```

### Production Deployment

#### Deploy All Services
```bash
# Standard deployment
just deploy

# OR with verbose output for detailed progress
just deploy-verbose
```

**Deployment Process Overview**:
The deployment runs through these phases automatically:

1. **System Preparation** (2-3 minutes)
   - Update package repositories
   - Install essential packages
   - Create service directories
   - Configure system timezone

2. **Security Hardening** (2-3 minutes)
   - Configure SSH with key-based authentication
   - Set up UFW firewall with restrictive rules
   - Install and configure fail2ban
   - Enable automatic security updates

3. **Docker Installation** (3-5 minutes)
   - Add Docker APT repository
   - Install Docker Engine and Docker Compose
   - Configure Docker daemon settings
   - Start and enable Docker service

4. **Authentication Service** (2-3 minutes)
   - Deploy Authelia configuration files
   - Start Authelia and Redis containers
   - Configure user database and access control

5. **Reverse Proxy** (2-3 minutes)
   - Generate Caddyfile with domain configuration
   - Deploy Caddy container
   - Obtain Let's Encrypt SSL certificates
   - Configure forward authentication

6. **Monitoring Stack** (3-5 minutes)
   - Deploy Prometheus with system targets
   - Set up Grafana with dashboards and datasources
   - Configure Loki for log aggregation
   - Deploy Promtail for log collection
   - Start Node Exporter for system metrics

**Total deployment time**: Typically 15-20 minutes

#### Monitor Deployment Progress
```bash
# In another terminal, monitor logs during deployment
just ssh "tail -f /var/log/syslog"

# Or monitor Docker container status
watch 'just ssh "docker ps --format \"table {{.Names}}\t{{.Status}}\""'
```

## Post-Installation Verification

### Automated Health Checks
```bash
# Run comprehensive health checks
just health-check

# This verifies:
# - VPS connectivity and system resources
# - All Docker containers are running
# - Service endpoints are responding
# - SSL certificates are valid
# - Authentication flow works correctly
```

### Manual Service Verification

#### Check Service Status
```bash
# View all running containers
just ssh "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

# Expected services:
# - caddy
# - authelia  
# - redis
# - grafana
# - prometheus
# - loki
# - promtail
# - node-exporter
```

#### Test Web Access
1. **Authentication Portal**:
   ```bash
   # Test auth portal accessibility
   curl -I https://auth.yourdomain.com
   # Should return: HTTP/2 200 OK
   ```

2. **Login and Setup 2FA**:
   - Visit: https://auth.yourdomain.com
   - Username: `admin` (not your email address)
   - Password: your configured password
   - Complete 2FA setup with authenticator app

3. **Protected Services**:
   - **Grafana**: https://grafana.yourdomain.com
   - **Prometheus**: https://prometheus.yourdomain.com  
   - **Loki**: https://loki.yourdomain.com
   - All should redirect to auth portal if not authenticated

#### SSL Certificate Verification
```bash
# Check certificate validity and expiration
echo | openssl s_client -connect yourdomain.com:443 -servername yourdomain.com 2>/dev/null | openssl x509 -noout -dates

# Verify certificate is from Let's Encrypt
curl -I https://auth.yourdomain.com | grep -i server
```

#### Service Logs Review
```bash
# Check for any errors in service logs
just logs caddy | tail -20
just logs authelia | tail -20  
just logs grafana | tail -20
just logs prometheus | tail -20

# Look for any ERROR or WARN messages
```

### Performance Verification

#### System Resource Check
```bash
# Check system resources
just ssh "free -h && df -h && uptime"

# Verify reasonable resource usage:
# - Memory usage should be < 80%
# - Disk usage should be < 80%  
# - Load average should be < number of CPU cores
```

#### Service Response Times
```bash
# Test service response times
time curl -s https://auth.yourdomain.com >/dev/null
time curl -s https://grafana.yourdomain.com >/dev/null
time curl -s https://prometheus.yourdomain.com >/dev/null

# Response times should typically be < 2 seconds
```

## Optional Configurations

### Email Notifications (SMTP)
To enable password reset emails and notifications:

```bash
# Edit environment file
vim ansible/inventories/production/.env

# Add SMTP configuration:
AUTHELIA_SMTP_HOST=smtp.gmail.com
AUTHELIA_SMTP_PORT=587
AUTHELIA_SMTP_USERNAME=your-email@gmail.com
AUTHELIA_SMTP_PASSWORD=your-app-specific-password
AUTHELIA_SENDER=noreply@yourdomain.com

# Redeploy Authelia
just deploy-authelia
```

### Custom Monitoring Targets
To add additional monitoring targets:

```bash
# Edit host variables
vim ansible/host_vars/vps/main.yml

# Add:
additional_prometheus_targets:
  - "192.168.1.50:9100"  # Additional server
  - "myapp:8080"         # Application endpoint

# Redeploy monitoring
just deploy --tags monitoring
```

### Resource Optimization
For VPS with limited resources:

```bash
# Edit global variables
vim ansible/group_vars/all.yml

# Reduce retention periods:
prometheus_retention_time: "7d"  # Reduce from 15d

# Add memory limits in docker-compose files:
# mem_limit: 256m  # for smaller services
# mem_limit: 512m  # for Grafana
# mem_limit: 1g    # for Prometheus
```

### Additional Security Hardening
```bash
# Change default SSH port for additional security
vim ansible/inventories/production.yml

# Add:
ssh_port: 2222  # Change from default 22

# Update firewall rules and redeploy
just deploy --tags security
```

### Backup Configuration
Set up automated backups:

```bash
# Create backup script directory
just ssh "mkdir -p /opt/scripts"

# Add to crontab for daily backups
just ssh "crontab -e"
# Add: 0 2 * * * /opt/scripts/backup.sh
```

## Installation Complete!

Your VPS is now fully configured with:

✅ **Security**: SSH hardening, firewall, fail2ban protection  
✅ **Authentication**: 2FA-protected access to all services  
✅ **Monitoring**: Comprehensive metrics and log aggregation  
✅ **SSL**: Automatic HTTPS certificates with Let's Encrypt  
✅ **Management**: Easy service management with just commands

### Next Steps:
1. **Explore Grafana**: Check out the monitoring dashboards
2. **Add custom services**: See [Customization Guide](customization.md)
3. **Set up alerts**: Configure monitoring alerts
4. **Plan backups**: Set up regular backup procedures
5. **Review security**: Follow [Security Guide](security.md) best practices

### Management Commands Reference:
```bash
# Health and status
just health-check          # Run health checks
just ping                  # Test connectivity

# Service management  
just restart <service>     # Restart specific service
just logs <service>        # View service logs

# Authentication
just authelia-hash 'pass'  # Generate password hash
just reset-authelia-bans   # Clear auth failures

# Deployment
just deploy               # Full redeployment
just deploy-authelia      # Deploy only auth service
```

For ongoing management and troubleshooting, refer to:
- [Management Guide](management.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Command Reference](commands.md)