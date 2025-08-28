# Command Reference

Complete reference for all available commands in the VPS configuration project.

## Table of Contents
- [Command Overview](#command-overview)
- [Testing & Validation Commands](#testing--validation-commands)
- [Deployment Commands](#deployment-commands)
- [Management Commands](#management-commands)
- [Authelia Commands](#authelia-commands)
- [Troubleshooting Commands](#troubleshooting-commands)
- [Python Script Commands](#python-script-commands)
- [Direct SSH Commands](#direct-ssh-commands)

## Command Overview

This project provides commands through two interfaces:
- **just**: Task runner with simplified commands (recommended)
- **uv run**: Direct Python script execution

All `just` commands can be viewed with:
```bash
just --list
```

## Testing & Validation Commands

### `just validate`
**Purpose**: Run quick validation tests (skips Docker image pulls)  
**Usage**: `just validate`  
**Equivalent**: `SKIP_DOCKER_PULL=true uv run validate`

Performs:
- Ansible syntax validation
- Configuration file checks
- Required tool verification
- Basic connectivity tests

```bash
# Example output
🔍 Running validation tests...
✅ Ansible configuration is valid
✅ Required tools are available
✅ Configuration files are present
✅ SSH connectivity works
```

### `just validate-full`
**Purpose**: Run comprehensive validation including Docker image checks  
**Usage**: `just validate-full`  
**Equivalent**: `uv run validate`

Additional checks beyond `validate`:
- Docker image availability
- Container registry connectivity
- Image version compatibility

### `just test-local`
**Purpose**: Test configuration locally using Docker containers  
**Usage**: `just test-local`  
**Equivalent**: `uv run test-local`

What it does:
1. Creates systemd-enabled Docker container
2. Applies full Ansible configuration
3. Starts all services locally
4. Runs health checks
5. Reports any issues

```bash
# Access local test services
ssh -p 2222 root@localhost        # SSH to test container
curl http://localhost:8080         # Test Caddy HTTP
curl http://localhost:3001         # Test Grafana
```

### `just test-clean`
**Purpose**: Clean up local test environment  
**Usage**: `just test-clean`

Removes:
- Test Docker containers
- Test Docker volumes
- Temporary test files

## Deployment Commands

### `just setup`
**Purpose**: Create production inventory file from template  
**Usage**: `just setup`

Creates `ansible/inventories/production.yml` from `hosts.yml` template if it doesn't exist.

### `just check`
**Purpose**: Validate Ansible playbook syntax  
**Usage**: `just check`  
**Equivalent**: `cd ansible && ansible-playbook playbooks/site.yml --syntax-check -i inventories/production.yml`

### `just dry-run`
**Purpose**: Test deployment without making changes  
**Usage**: `just dry-run`  
**Equivalent**: `cd ansible && ansible-playbook playbooks/site.yml -i inventories/production.yml --check`

Shows exactly what would be changed during deployment.

### `just deploy`
**Purpose**: Deploy all services to production VPS  
**Usage**: `just deploy`  
**Equivalent**: `cd ansible && ansible-playbook playbooks/site.yml -i inventories/production.yml`

Full deployment process:
1. System preparation and hardening
2. Docker installation
3. Service deployment
4. SSL certificate acquisition
5. Health checks

### `just deploy-verbose`
**Purpose**: Deploy with detailed Ansible output  
**Usage**: `just deploy-verbose`  
**Equivalent**: `cd ansible && ansible-playbook playbooks/site.yml -i inventories/production.yml -v`

Use for troubleshooting deployment issues.

### `just deploy-authelia`
**Purpose**: Deploy only Authelia authentication service  
**Usage**: `just deploy-authelia`  
**Equivalent**: `cd ansible && ansible-playbook playbooks/site.yml -i inventories/production.yml --tags authelia`

Useful for:
- Updating Authelia configuration
- Adding/modifying users
- Changing authentication settings

## Management Commands

### `just ping`
**Purpose**: Test VPS connectivity through Ansible  
**Usage**: `just ping`  
**Equivalent**: `cd ansible && ansible vps -i inventories/production.yml -m ping`

### `just health-check`
**Purpose**: Run comprehensive health checks on deployed system  
**Usage**: `just health-check`  
**Equivalent**: `uv run health-check production`

Checks:
- VPS connectivity and system resources
- Docker container status
- Service endpoint availability
- SSL certificate validity
- Authentication flow functionality

### `just restart <service>`
**Purpose**: Restart specific Docker service  
**Usage**: `just restart grafana`  
**Equivalent**: `cd ansible && ansible vps -i inventories/production.yml -m shell -a "docker restart grafana"`

**Available services**:
- `caddy` - Reverse proxy
- `authelia` - Authentication service
- `redis` - Session storage
- `grafana` - Dashboard service
- `prometheus` - Metrics collection
- `loki` - Log aggregation
- `promtail` - Log collection
- `node-exporter` - System metrics

### `just logs <service>`
**Purpose**: View logs for specific service  
**Usage**: `just logs prometheus`  
**Options**: Add `--tail N` for last N lines  
**Equivalent**: `cd ansible && ansible vps -i inventories/production.yml -m shell -a "docker logs --tail 50 prometheus"`

Examples:
```bash
just logs caddy              # View Caddy logs
just logs authelia --tail 100  # Last 100 lines of Authelia logs
just logs grafana | grep ERROR # Filter for errors
```

### `just ssh`
**Purpose**: Quick VPS connection test  
**Usage**: `just ssh`  
**Equivalent**: `cd ansible && ansible vps -i inventories/production.yml -m shell -a "uptime"`

For interactive SSH session:
```bash
# Get connection details from inventory
ssh ubuntu@YOUR_VPS_IP
```

### `just clean`
**Purpose**: Clean temporary files  
**Usage**: `just clean`

Removes:
- Ansible retry files (*.retry)
- Temporary configuration files
- Local cache files

## Authelia Commands

### `just authelia-hash <password>`
**Purpose**: Generate Argon2 password hash for Authelia users  
**Usage**: `just authelia-hash 'my-secure-password'`  
**Equivalent**: `docker run --rm authelia/authelia:latest authelia crypto hash generate argon2 --password 'my-secure-password'`

Example:
```bash
just authelia-hash 'MySecurePassword123!'
# Output: $argon2id$v=19$m=65536,t=3,p=4$...
```

**Important**: 
- Use single quotes to prevent shell interpretation
- Copy the entire hash output
- Do not include quotes when adding to environment file

### `just reset-authelia-bans`
**Purpose**: Clear Authelia user bans and regulation database  
**Usage**: `just reset-authelia-bans`

What it does:
1. Removes regulation database (`/data/db.sqlite3`)
2. Restarts Authelia service
3. Clears all failed login attempts and temporary bans

Use when:
- Account is temporarily banned due to failed attempts
- Need to reset authentication attempt counters
- Troubleshooting login issues

### `just update-caddy`
**Purpose**: Update only Caddy configuration and restart service  
**Usage**: `just update-caddy`

Process:
1. Generates new Caddyfile from template
2. Copies to VPS
3. Restarts Caddy container
4. Triggers SSL certificate renewal if needed

## Troubleshooting Commands

### Service Status Commands
```bash
# Check all containers
just ssh "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

# Check container resource usage
just ssh "docker stats --no-stream"

# Check system resources
just ssh "free -h && df -h && uptime"
```

### Log Analysis Commands
```bash
# Search for errors across all services
just logs caddy | grep -i error
just logs authelia | grep -i failed
just logs grafana | grep -i error

# View system logs
just ssh "sudo journalctl -u docker --since '1 hour ago'"

# Check firewall logs
just ssh "sudo tail -f /var/log/ufw.log"
```

### Network Troubleshooting
```bash
# Check port accessibility
just ssh "sudo ss -tlnp | grep :443"

# Test internal service connectivity
just ssh "docker exec caddy ping authelia"
just ssh "docker exec grafana wget -qO- http://prometheus:9090/api/v1/query?query=up"

# Check DNS resolution
nslookup auth.yourdomain.com
dig A grafana.yourdomain.com
```

### SSL Certificate Commands
```bash
# Check certificate status
just ssh "docker exec caddy caddy list-certificates"

# Check certificate expiration
echo | openssl s_client -connect yourdomain.com:443 -servername yourdomain.com 2>/dev/null | openssl x509 -noout -dates

# Force certificate renewal
just restart caddy
```

## Python Script Commands

### `uv run validate`
**Purpose**: Run validation script directly  
**Options**:
- No options: Full validation including Docker images
- `SKIP_DOCKER_PULL=true`: Skip Docker image validation

### `uv run test-local`
**Purpose**: Run local testing script directly  
**Process**:
1. Builds test Docker environment
2. Applies Ansible configuration
3. Validates deployment
4. Provides access information

### `uv run health-check <environment>`
**Purpose**: Run health check script directly  
**Usage**: `uv run health-check production`

**Check Categories**:
- **Connectivity**: SSH and basic network tests
- **System Resources**: CPU, memory, disk usage
- **Services**: Docker container status and health
- **Endpoints**: HTTP/HTTPS service availability
- **Authentication**: Login flow testing

### `uv run deploy <environment> <action>`
**Purpose**: Run deployment script with specific actions  
**Usage**: `uv run deploy production apply`

**Available Actions**:
- `check`: Syntax validation only
- `plan`: Dry-run deployment (show changes)
- `apply`: Execute deployment
- `cleanup`: Clean up deployment artifacts

## Direct SSH Commands

For direct VPS management:

### System Management
```bash
# Connect to VPS
ssh ubuntu@YOUR_VPS_IP

# Check system status
sudo systemctl status docker
sudo systemctl status ssh
sudo ufw status

# Update system packages
sudo apt update && sudo apt upgrade -y

# Reboot system (if needed)
sudo reboot
```

### Docker Management
```bash
# View all containers
docker ps -a

# View Docker logs
docker logs <container-name>

# Execute commands in containers
docker exec -it grafana /bin/sh
docker exec authelia authelia --help

# Clean up Docker resources
docker system prune -f
docker image prune -a -f
```

### Service Configuration
```bash
# View service configurations
cat /opt/caddy/Caddyfile
cat /opt/authelia/config/configuration.yml
cat /opt/prometheus/prometheus.yml

# Check service data directories
ls -la /opt/grafana/data/
ls -la /opt/prometheus/data/
ls -la /opt/authelia/data/
```

### Log Management
```bash
# View service logs
tail -f /opt/logs/caddy.log
tail -f /opt/logs/authelia.log

# View system logs
sudo journalctl -f
sudo tail -f /var/log/syslog

# Rotate logs
sudo logrotate -f /etc/logrotate.d/docker-container
```

## Environment-Specific Commands

### Development/Testing
```bash
# Use test inventory
just deploy --inventory inventories/test.yml

# Deploy specific roles
just deploy --tags common,security
just deploy --tags monitoring
```

### Production Operations
```bash
# Backup before major changes
just ssh "tar -czf /tmp/backup-$(date +%Y%m%d).tar.gz /opt/"

# Monitor deployment progress
watch 'just ssh "docker ps --format \"table {{.Names}}\t{{.Status}}\""'

# Check service health after deployment
just health-check
```

## Command Troubleshooting

### Common Issues

#### Permission Errors
```bash
# Fix SSH key permissions
chmod 600 ~/.ssh/id_rsa

# Fix Ansible inventory permissions
chmod 644 ansible/inventories/production.yml
```

#### Network Issues
```bash
# Test basic connectivity
ping YOUR_VPS_IP

# Test SSH connectivity
ssh -v ubuntu@YOUR_VPS_IP

# Check firewall rules
just ssh "sudo ufw status verbose"
```

#### Docker Issues
```bash
# Restart Docker daemon
just ssh "sudo systemctl restart docker"

# Check Docker daemon status
just ssh "sudo systemctl status docker"

# View Docker daemon logs
just ssh "sudo journalctl -u docker --since '1 hour ago'"
```

## Tips and Best Practices

### Command Execution Best Practices
1. **Always test locally first**: Use `just test-local` before production deployment
2. **Use dry-run**: Run `just dry-run` to preview changes
3. **Monitor logs**: Watch service logs during deployment
4. **Health checks**: Run `just health-check` after any changes
5. **Backup first**: Create backups before major changes

### Efficient Workflow
```bash
# Typical deployment workflow
just validate-full        # Comprehensive validation
just test-local           # Test locally
just check                # Syntax check
just dry-run              # Preview changes
just deploy               # Deploy to production
just health-check         # Verify deployment
```

### Debugging Commands
```bash
# Get detailed information for troubleshooting
just ssh "uname -a && lsb_release -a"
just ssh "docker --version && docker-compose --version"
just ssh "free -h && df -h && uptime"
just ssh "docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'"
```

This command reference covers all available commands for managing your VPS configuration. For specific use cases and workflows, refer to other documentation sections.