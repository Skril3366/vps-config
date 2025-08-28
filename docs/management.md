# Management Guide

This guide covers day-to-day operational tasks for managing your VPS configuration after deployment.

## Table of Contents
- [Daily Operations](#daily-operations)
- [Service Management](#service-management)
- [User Management](#user-management)
- [Monitoring and Alerts](#monitoring-and-alerts)
- [Backup and Recovery](#backup-and-recovery)
- [Updates and Maintenance](#updates-and-maintenance)
- [Security Management](#security-management)
- [Performance Optimization](#performance-optimization)

## Daily Operations

### Health Monitoring
```bash
# Daily health check (recommended)
just health-check

# Check system resources
just ssh "free -h && df -h && uptime"

# Review recent logs for issues
just logs caddy | tail -20
just logs authelia | grep -i error
just logs grafana | tail -10
```

### Service Status Check
```bash
# Quick overview of all services
just ssh "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

# Check for any failed containers
just ssh "docker ps -a --filter 'status=exited'"

# View resource usage
just ssh "docker stats --no-stream"
```

### Certificate Monitoring
```bash
# Check SSL certificate expiration
echo | openssl s_client -connect yourdomain.com:443 -servername yourdomain.com 2>/dev/null | openssl x509 -noout -dates

# List all certificates
just ssh "docker exec caddy caddy list-certificates"
```

## Service Management

### Starting and Stopping Services

#### Individual Service Management
```bash
# Restart specific services
just restart caddy           # Reverse proxy
just restart authelia        # Authentication
just restart grafana         # Dashboards
just restart prometheus      # Metrics
just restart loki           # Log aggregation

# Stop a service (use with caution)
just ssh "docker stop grafana"

# Start a stopped service
just ssh "docker start grafana"
```

#### Full Stack Management
```bash
# Stop all services
just ssh "docker stop \$(docker ps -q)"

# Start all services
just ssh "cd /opt && docker-compose up -d"

# Restart entire stack
just ssh "cd /opt && docker-compose restart"
```

### Service Logs and Debugging

#### Log Viewing
```bash
# View recent logs
just logs <service-name>

# Follow logs in real-time
just ssh "docker logs -f caddy"

# View logs with timestamps
just ssh "docker logs -t prometheus"

# View last N lines
just logs authelia --tail 50
```

#### Log Analysis
```bash
# Search for specific errors
just logs caddy | grep -i "error\|fail"
just logs authelia | grep -i "authentication failed"
just logs grafana | grep -i "database"

# Check for certificate issues
just logs caddy | grep -i "certificate\|acme\|ssl"

# Monitor authentication attempts
just logs authelia | grep -i "login\|authentication"
```

### Configuration Updates

#### Update Service Configuration
```bash
# Update Caddy configuration only
just update-caddy

# Update Authelia configuration
just deploy-authelia

# Full configuration update
just deploy
```

#### Adding New Services
1. **Edit Docker Compose**: Add service definition
2. **Update Caddy**: Add reverse proxy configuration
3. **Update DNS**: Add subdomain DNS record
4. **Deploy**: Run `just deploy` or `just update-caddy`

Example adding new service:
```caddy
# In Caddyfile template
myapp.yourdomain.com {
    forward_auth authelia:9091 {
        uri /api/verify?rd=https://auth.yourdomain.com/
    }
    reverse_proxy myapp:8080
}
```

## User Management

### Authelia User Administration

#### Adding New Users
1. **Generate password hash**:
   ```bash
   just authelia-hash 'user-password'
   ```

2. **Edit user database**:
   ```bash
   vim ansible/roles/authelia/templates/users_database.yml.j2
   ```
   
   Add user:
   ```yaml
   users:
     newuser:
       displayname: "New User"
       password: "$argon2id$v=19$m=65536,t=3,p=4$..."
       email: "newuser@yourdomain.com"
       groups:
         - users
   ```

3. **Redeploy Authelia**:
   ```bash
   just deploy-authelia
   ```

#### Managing User Access
```yaml
# In users_database.yml.j2
groups:
  - name: admins
    description: "Full access to all services"
  
  - name: users
    description: "Limited access to monitoring"
  
  - name: developers
    description: "Access to development tools"
```

#### User Troubleshooting
```bash
# Reset user 2FA (emergency only)
just ssh "sqlite3 /opt/authelia/data/db.sqlite3 'DELETE FROM totp_configurations WHERE username=\"username\";'"

# Clear user bans
just reset-authelia-bans

# Check user sessions
just ssh "docker exec redis redis-cli KEYS 'authelia:*'"

# Clear all sessions
just ssh "docker exec redis redis-cli FLUSHALL"
```

### SSH User Management

#### Add SSH Users
```bash
# Create new user
just ssh "sudo adduser newuser"

# Add to sudo group
just ssh "sudo usermod -aG sudo newuser"

# Setup SSH key access
just ssh "sudo mkdir -p /home/newuser/.ssh"
just ssh "sudo cp ~/.ssh/authorized_keys /home/newuser/.ssh/"
just ssh "sudo chown -R newuser:newuser /home/newuser/.ssh"
just ssh "sudo chmod 700 /home/newuser/.ssh"
just ssh "sudo chmod 600 /home/newuser/.ssh/authorized_keys"
```

## Monitoring and Alerts

### Grafana Dashboard Management

#### Accessing Dashboards
- **System Overview**: https://grafana.yourdomain.com/d/system
- **Docker Overview**: https://grafana.yourdomain.com/d/docker
- **Logs Overview**: https://grafana.yourdomain.com/d/logs

#### Creating Custom Dashboards
1. **Login to Grafana**: https://grafana.yourdomain.com
2. **Create Dashboard**: Click "+" → "Dashboard"
3. **Add Panel**: Click "Add new panel"
4. **Configure Query**: Select Prometheus/Loki datasource
5. **Save Dashboard**: Give it a descriptive name

#### Useful Prometheus Queries
```bash
# CPU usage percentage
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage percentage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Disk usage percentage
100 - ((node_filesystem_free_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)

# Container CPU usage
rate(container_cpu_usage_seconds_total{name!=""}[5m])
```

### Log Analysis with Loki

#### Useful Log Queries (LogQL)
```bash
# All container logs
{job="containerlogs"}

# Errors across all services
{job="containerlogs"} |= "error" or "ERROR"

# Authentication failures
{job="containerlogs", container_name="authelia"} |= "failed"

# Caddy access logs
{job="containerlogs", container_name="caddy"} | json

# Rate of log entries
rate({job="containerlogs"}[5m])
```

### Setting Up Alerts

#### Prometheus Alert Rules
Edit `ansible/roles/monitoring/templates/alert_rules.yml.j2`:

```yaml
groups:
  - name: system-alerts
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for more than 5 minutes"

      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is above 90% for more than 5 minutes"

      - alert: DiskSpaceLow
        expr: 100 - ((node_filesystem_free_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100) > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space"
          description: "Disk usage is above 85%"
```

## Backup and Recovery

### Regular Backup Tasks

#### Configuration Backup
```bash
# Create configuration backup
just ssh "sudo tar -czf /tmp/config-backup-\$(date +%Y%m%d).tar.gz /opt/ --exclude='*/data/*' --exclude='*/logs/*'"

# Download backup locally
scp ubuntu@YOUR_VPS_IP:/tmp/config-backup-*.tar.gz ./backups/
```

#### Data Backup
```bash
# Backup all persistent data
just ssh "sudo tar -czf /tmp/data-backup-\$(date +%Y%m%d).tar.gz /opt/*/data/"

# Backup specific services
just ssh "sudo tar -czf /tmp/grafana-backup-\$(date +%Y%m%d).tar.gz /opt/grafana/data/"
just ssh "sudo tar -czf /tmp/prometheus-backup-\$(date +%Y%m%d).tar.gz /opt/prometheus/data/"
```

#### Automated Backup Script
Create `/opt/scripts/backup.sh`:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"
mkdir -p $BACKUP_DIR

# Configuration backup
tar -czf $BACKUP_DIR/config-$DATE.tar.gz /opt/ --exclude='*/data/*' --exclude='*/logs/*'

# Data backup
tar -czf $BACKUP_DIR/data-$DATE.tar.gz /opt/*/data/

# Clean old backups (keep 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * /opt/scripts/backup.sh >> /var/log/backup.log 2>&1
```

### Recovery Procedures

#### Service Recovery
```bash
# Stop problematic service
just ssh "docker stop <service>"

# Remove container
just ssh "docker rm <service>"

# Redeploy service
just deploy --tags <service>
```

#### Data Recovery
```bash
# Stop services
just ssh "docker-compose -f /opt/docker-compose.yml down"

# Restore data from backup
just ssh "sudo tar -xzf /tmp/data-backup-YYYYMMDD.tar.gz -C /"

# Start services
just ssh "docker-compose -f /opt/docker-compose.yml up -d"
```

#### Full System Recovery
```bash
# Emergency deployment from scratch
just deploy

# Restore data if needed
just ssh "sudo tar -xzf /path/to/backup.tar.gz -C /"

# Restart all services
just ssh "docker-compose restart"
```

## Updates and Maintenance

### System Updates

#### Regular System Maintenance
```bash
# Update system packages (automatic with unattended-upgrades)
just ssh "sudo apt update && sudo apt upgrade -y"

# Clean package cache
just ssh "sudo apt autoremove -y && sudo apt autoclean"

# Check for required reboots
just ssh "[ -f /var/run/reboot-required ] && echo 'Reboot required' || echo 'No reboot needed'"
```

#### Docker Updates
```bash
# Update Docker images
just ssh "docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}'"

# Pull latest images
just ssh "docker-compose pull"

# Restart with new images
just ssh "docker-compose up -d"

# Clean old images
just ssh "docker image prune -a -f"
```

### Application Updates

#### Update Service Versions
Edit `ansible/group_vars/all.yml`:
```yaml
# Update to specific versions
caddy_image: "caddy:2.7-alpine"
authelia_image: "authelia/authelia:4.38"
prometheus_image: "prom/prometheus:v2.45.0"
grafana_image: "grafana/grafana:10.2.0"
```

Then redeploy:
```bash
just deploy
```

#### Configuration Updates
```bash
# Update global configuration
vim ansible/group_vars/all.yml

# Update service-specific configuration
vim ansible/roles/<service>/templates/*.j2

# Apply changes
just deploy
```

### Maintenance Windows

#### Planned Maintenance Process
1. **Notify users** (if applicable)
2. **Create backup**: `just ssh "tar -czf /tmp/pre-maintenance-backup.tar.gz /opt/"`
3. **Test changes locally**: `just test-local`
4. **Apply updates**: `just deploy`
5. **Verify services**: `just health-check`
6. **Monitor logs**: Check for any issues

#### Emergency Maintenance
```bash
# Quick restart of problematic service
just restart <service>

# Emergency rollback
git checkout HEAD~1 -- ansible/
just deploy

# Emergency stop of all services
just ssh "docker stop \$(docker ps -q)"
```

## Security Management

### Regular Security Tasks

#### Review Authentication Logs
```bash
# Check failed authentication attempts
just logs authelia | grep -i "authentication failed" | tail -20

# Check SSH login attempts
just ssh "sudo grep 'Failed password' /var/log/auth.log | tail -10"

# Check fail2ban status
just ssh "sudo fail2ban-client status"
```

#### SSL Certificate Monitoring
```bash
# Check certificate expiration dates
echo | openssl s_client -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates

# Automated certificate renewal is handled by Caddy
# Manual renewal if needed:
just restart caddy
```

#### Security Updates
```bash
# Check for security updates (handled automatically)
just ssh "sudo unattended-upgrades --dry-run -d"

# View update logs
just ssh "sudo tail -f /var/log/unattended-upgrades/unattended-upgrades.log"
```

### Access Control Management

#### Review User Access
```bash
# Check active sessions
just ssh "docker exec redis redis-cli KEYS 'authelia:*'"

# Review user database
just ssh "cat /opt/authelia/config/users_database.yml"

# Check SSH users
just ssh "cut -d: -f1 /etc/passwd | grep -v '^_'"
```

#### Firewall Management
```bash
# Check firewall status
just ssh "sudo ufw status verbose"

# View recent firewall logs
just ssh "sudo tail -20 /var/log/ufw.log"

# Add temporary rule (if needed)
just ssh "sudo ufw allow from TRUSTED_IP to any port 22"
```

## Performance Optimization

### Resource Monitoring

#### Regular Performance Checks
```bash
# System resource usage
just ssh "top -bn1 | head -20"

# Memory usage by process
just ssh "ps aux --sort=-%mem | head -10"

# Disk I/O statistics
just ssh "iostat -x 1 5"

# Network usage
just ssh "iftop -t -s 10"
```

#### Container Performance
```bash
# Container resource usage
just ssh "docker stats --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'"

# Container process analysis
just ssh "docker exec grafana ps aux"

# Check container health
just ssh "docker inspect --format='{{.State.Health.Status}}' grafana"
```

### Optimization Techniques

#### Memory Optimization
```yaml
# In docker-compose.yml, add memory limits
services:
  grafana:
    mem_limit: 512m
  prometheus:
    mem_limit: 1g
  authelia:
    mem_limit: 256m
```

#### Storage Optimization
```bash
# Clean up Docker resources
just ssh "docker system prune -f"

# Remove unused volumes
just ssh "docker volume prune -f"

# Compress old logs
just ssh "sudo logrotate -f /etc/logrotate.conf"

# Check largest files
just ssh "sudo find /opt -type f -size +100M -exec ls -lh {} +"
```

#### Database Optimization
```bash
# Optimize Prometheus storage
just ssh "docker exec prometheus promtool tsdb analyze /prometheus"

# Optimize Authelia SQLite database
just ssh "docker exec authelia sqlite3 /data/db.sqlite3 'VACUUM; ANALYZE;'"
```

This management guide provides comprehensive procedures for day-to-day operations of your VPS configuration. Regular execution of these tasks will ensure optimal performance, security, and reliability of your system.