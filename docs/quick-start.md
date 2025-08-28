# Quick Start Guide

Get your VPS up and running with monitoring, authentication, and reverse proxy in under 30 minutes.

## Prerequisites

Before starting, ensure you have:

- **VPS**: Ubuntu 20.04+ with 2GB RAM, public IP
- **Domain**: A domain with DNS access (pointing to your VPS IP)
- **Local tools**: `just`, `uv`, `docker` installed
- **SSH access**: Key-based SSH access to your VPS with sudo privileges

## Step 1: Initial Setup (5 minutes)

### Clone and Initialize
```bash
# Clone the repository
git clone <your-repo-url>
cd vps-config

# Install dependencies
uv sync

# Verify setup
just validate
```

### Configure Your VPS Details
```bash
# Create production inventory
just setup

# Edit with your VPS details
vim ansible/inventories/production.yml
```

Edit the key values:
```yaml
all:
  hosts:
    vps:
      ansible_host: "YOUR_VPS_IP"
      ansible_user: "ubuntu"  # or your SSH user
      ansible_ssh_private_key_file: "~/.ssh/your_key"
  vars:
    domain_name: "yourdomain.com"
    letsencrypt_email: "admin@yourdomain.com"
```

### Test Connectivity
```bash
# Verify SSH connection to your VPS
just ping
# Should return: vps | SUCCESS => {"changed": false, "ping": "pong"}
```

## Step 2: Configure DNS (5 minutes)

Add these DNS records pointing to your VPS IP:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | yourdomain.com | YOUR_VPS_IP | 300 |
| A | auth.yourdomain.com | YOUR_VPS_IP | 300 |
| A | grafana.yourdomain.com | YOUR_VPS_IP | 300 |
| A | prometheus.yourdomain.com | YOUR_VPS_IP | 300 |
| A | loki.yourdomain.com | YOUR_VPS_IP | 300 |

**Verify DNS propagation**:
```bash
# Check DNS resolution
nslookup auth.yourdomain.com
```

## Step 3: Configure Authentication (10 minutes)

**⚠️ This step is required before deployment!**

### Generate Secure Secrets
```bash
# Generate three random secrets (copy these!)
echo "JWT Secret: $(openssl rand -base64 32)"
echo "Session Secret: $(openssl rand -base64 32)"  
echo "Storage Key: $(openssl rand -base64 32)"
```

### Generate Admin Password Hash
```bash
# Replace 'your-secure-password' with your actual password
just authelia-hash 'your-secure-password'
# Copy the entire hash output (starting with $argon2id$...)
```

### Create Environment File
```bash
# Create the environment file
mkdir -p ansible/inventories/production
cp .env.example ansible/inventories/production/.env

# Edit the environment file
vim ansible/inventories/production/.env
```

Update with your values:
```bash
# Use the secrets generated above (keep the quotes)
AUTHELIA_JWT_SECRET="your_generated_jwt_secret"
AUTHELIA_SESSION_SECRET="your_generated_session_secret"
AUTHELIA_STORAGE_ENCRYPTION_KEY="your_generated_storage_key"

# Admin user details
AUTHELIA_ADMIN_USER=admin
AUTHELIA_ADMIN_DISPLAYNAME=Administrator
AUTHELIA_ADMIN_EMAIL=admin@yourdomain.com

# Password hash (NO QUOTES around the hash!)
AUTHELIA_ADMIN_PASSWORD_HASH=$argon2id$v=19$m=65536,t=3,p=4$your_hash_here
```

## Step 4: Test Locally (5 minutes)

```bash
# Test configuration locally with Docker
just test-local

# This will:
# 1. Create a test environment
# 2. Deploy all services
# 3. Run health checks
# 4. Report any issues
```

**Expected output**: All services should start successfully and pass health checks.

If there are issues, check:
- Environment file has correct values
- No syntax errors in configuration
- All required secrets are set

```bash
# Clean up test environment
just test-clean
```

## Step 5: Deploy to Production (5 minutes)

### Pre-deployment Checks
```bash
# Check Ansible syntax
just check

# Test what will be deployed (dry-run)
just dry-run
```

### Deploy All Services
```bash
# Deploy everything
just deploy

# Or with verbose output for troubleshooting
just deploy-verbose
```

**What happens during deployment**:
1. ✅ System updates and package installation
2. ✅ SSH hardening and firewall configuration  
3. ✅ Docker installation and setup
4. ✅ Service deployment (Authelia, Caddy, Prometheus, Grafana, Loki)
5. ✅ SSL certificate acquisition
6. ✅ Service integration and health checks

## Step 6: Verify Deployment (5 minutes)

### Run Health Checks
```bash
# Comprehensive health check
just health-check

# Expected: All checks should pass ✅
```

### Test Service Access

1. **Visit auth portal**: https://auth.yourdomain.com
   - Should show Authelia login page
   - Login with username `admin` and your password
   - Complete 2FA setup with your authenticator app

2. **Test protected services**:
   - **Grafana**: https://grafana.yourdomain.com
   - **Prometheus**: https://prometheus.yourdomain.com
   - **Loki**: https://loki.yourdomain.com
   - All should redirect to auth portal if not logged in

### Check SSL Certificates
```bash
# Verify HTTPS is working
curl -I https://auth.yourdomain.com
# Should return: HTTP/2 200 with valid SSL certificate
```

## Quick Verification Checklist

After deployment, verify:

- [ ] **DNS**: All subdomains resolve to VPS IP
- [ ] **SSH**: Can still access VPS via SSH
- [ ] **HTTPS**: All services accessible via HTTPS
- [ ] **Authentication**: Can login at auth.yourdomain.com
- [ ] **2FA**: Two-factor authentication setup completed
- [ ] **Services**: All protected services accessible after authentication
- [ ] **Monitoring**: Grafana shows system metrics
- [ ] **Health**: `just health-check` passes all tests

## Common Quick Fixes

### Can't Login to Authelia
```bash
# Check username (use 'admin', not email)
# Check password hash generation
just authelia-hash 'your-password'

# Reset bans if account is locked
just reset-authelia-bans
```

### Services Return 502 Errors
```bash
# Check all containers are running
just ssh "docker ps"

# Restart problematic service
just restart <service-name>

# Check logs
just logs <service-name>
```

### SSL Certificate Issues
```bash
# Check DNS is pointing to correct IP
dig A yourdomain.com

# Restart Caddy to retry certificate
just restart caddy

# Check Caddy logs for certificate errors
just logs caddy | grep -i certificate
```

## Next Steps

Now that your VPS is running:

1. **Explore Grafana**: Check out the pre-configured dashboards
2. **Add applications**: See [Customization Guide](customization.md) to add your own services
3. **Set up monitoring**: Configure alerts and notifications
4. **Security review**: Review the [Security Guide](security.md)
5. **Backup setup**: Plan your backup strategy

## Getting Help

If you encounter issues:

1. **Check logs**: `just logs <service-name>`
2. **Health check**: `just health-check`
3. **Review troubleshooting**: [Troubleshooting Guide](troubleshooting.md)
4. **Check configuration**: [Configuration Guide](configuration.md)

## Summary of Commands

```bash
# Setup
just setup              # Create production inventory
just validate           # Validate configuration
just test-local         # Test locally

# Deploy
just check              # Check syntax
just dry-run            # Test deployment
just deploy             # Deploy to production

# Manage
just health-check       # Check system health
just restart <service>  # Restart service
just logs <service>     # View logs

# Authelia
just authelia-hash 'pass'      # Generate password hash
just reset-authelia-bans       # Clear user bans
just deploy-authelia           # Deploy only auth service
```

**Congratulations! 🎉** Your VPS is now running with:
- ✅ Secure authentication with 2FA
- ✅ Automatic HTTPS with Let's Encrypt
- ✅ Comprehensive monitoring and logging
- ✅ Security hardening and firewall
- ✅ Easy management with just commands