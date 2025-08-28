# Security Guide

Comprehensive security guide covering best practices, hardening measures, and security maintenance for your VPS configuration.

## Table of Contents
- [Security Overview](#security-overview)
- [Built-in Security Features](#built-in-security-features)
- [Additional Hardening](#additional-hardening)
- [Access Control](#access-control)
- [SSL/TLS Security](#ssltls-security)
- [Monitoring and Alerting](#monitoring-and-alerting)
- [Incident Response](#incident-response)
- [Security Maintenance](#security-maintenance)

## Security Overview

The VPS configuration implements defense-in-depth security with multiple layers:

```
Internet → Firewall → Reverse Proxy → Authentication → Services
    ↓         ↓           ↓              ↓            ↓
 DDoS Prot. UFW Rules  Caddy/TLS    Authelia     Container
 Rate Limit fail2ban   Rate Limit    2FA/MFA     Isolation
```

### Security Principles
- **Least Privilege**: Users and services have minimum required access
- **Defense in Depth**: Multiple security layers
- **Fail Secure**: Secure defaults when systems fail
- **Continuous Monitoring**: Real-time security monitoring
- **Regular Updates**: Automated security patching

## Built-in Security Features

### System-Level Security

#### SSH Hardening
Automatically configured during deployment:

```yaml
# SSH Configuration (applied automatically)
ssh_permit_root_login: "no"       # Disable root login
ssh_password_authentication: "no" # Require SSH keys
ssh_pubkey_authentication: "yes"  # Enable key auth
ssh_max_auth_tries: 3            # Limit login attempts
ssh_client_alive_interval: 300    # Keep-alive timeout
ssh_client_alive_count_max: 2     # Max keep-alive packets
```

**Verification**:
```bash
# Check SSH configuration
just ssh "sudo sshd -T | grep -i 'permitrootlogin\|passwordauth\|pubkeyauth'"

# View SSH logs
just ssh "sudo grep 'sshd' /var/log/auth.log | tail -10"
```

#### Firewall Protection (UFW)
Default firewall rules:

```bash
# Allowed ports
22/tcp    # SSH (configurable)
80/tcp    # HTTP (Caddy - redirects to HTTPS)
443/tcp   # HTTPS (Caddy)

# Default policies
Incoming: DENY
Outgoing: ALLOW
Routed: DENY
```

**Management**:
```bash
# Check firewall status
just ssh "sudo ufw status verbose"

# View firewall logs
just ssh "sudo tail -20 /var/log/ufw.log"

# Add temporary rule for trusted IP
just ssh "sudo ufw allow from TRUSTED_IP to any port 22"
```

#### Intrusion Detection (fail2ban)
Automatic IP banning for suspicious activity:

**Default Jails**:
- **SSH**: Ban IPs after 5 failed attempts (1 hour ban)
- **Caddy**: Ban IPs after 10 failed HTTP requests (30 min ban)

**Management**:
```bash
# Check fail2ban status
just ssh "sudo fail2ban-client status"

# Check SSH jail
just ssh "sudo fail2ban-client status sshd"

# Unban IP (if needed)
just ssh "sudo fail2ban-client set sshd unbanip IP_ADDRESS"

# View banned IPs
just ssh "sudo fail2ban-client banned"
```

### Application Security

#### Authentication and Authorization (Authelia)
- **Multi-Factor Authentication**: TOTP-based 2FA required
- **Session Management**: Secure session handling with Redis
- **Access Control**: Rule-based access to services
- **Rate Limiting**: Prevents brute force attacks

**Security Features**:
```yaml
# Authelia security settings
regulation:
  max_retries: 10          # Max failed attempts
  find_time: 2m            # Time window for attempts
  ban_time: 5m             # Ban duration (lenient)

session:
  expiration: 1h           # Session timeout
  inactivity: 5m           # Inactivity timeout
  remember_me_duration: 1M # Remember me period
```

#### SSL/TLS Security
- **Automatic HTTPS**: Let's Encrypt certificates
- **HTTP to HTTPS**: Automatic redirection
- **Modern TLS**: TLS 1.2+ with secure ciphers
- **HSTS**: HTTP Strict Transport Security headers

### Container Security
- **Isolation**: All services run in isolated containers
- **Non-root Users**: Services run as non-privileged users
- **Network Segmentation**: Services communicate through defined networks
- **Resource Limits**: CPU and memory limits prevent resource exhaustion

## Additional Hardening

### SSH Security Enhancements

#### Change Default SSH Port
```yaml
# In ansible/inventories/production.yml
vars:
  ssh_port: 2222  # Change from default 22
```

Then redeploy:
```bash
just deploy --tags security
```

#### SSH Key Management
```bash
# Generate new SSH key pair (if needed)
ssh-keygen -t ed25519 -C "your-email@example.com"

# Add key to ssh-agent
ssh-add ~/.ssh/id_ed25519

# Copy public key to VPS
ssh-copy-id -i ~/.ssh/id_ed25519.pub ubuntu@YOUR_VPS_IP
```

#### Disable SSH for Specific Users
```yaml
# In group_vars/all.yml
ssh_deny_users:
  - root
  - git
  - www-data
```

### System Hardening

#### Kernel Security Parameters
Add to system configuration:
```bash
# /etc/sysctl.d/99-security.conf
net.ipv4.ip_forward = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
```

#### File System Security
```bash
# Set secure permissions on sensitive files
just ssh "sudo chmod 600 /opt/authelia/.env"
just ssh "sudo chmod 600 /opt/authelia/config/configuration.yml"
just ssh "sudo chown -R root:root /opt/*/config/"
```

#### Automatic Security Updates
Already enabled by default:
```yaml
unattended_upgrades_enabled: true
automatic_reboot: false  # Set to true for automatic reboots
```

**Monitor Updates**:
```bash
# Check update logs
just ssh "sudo tail -20 /var/log/unattended-upgrades/unattended-upgrades.log"

# Check pending updates
just ssh "sudo apt list --upgradable"
```

### Network Security

#### Rate Limiting
Configure rate limiting in Caddy:
```caddy
# In Caddyfile template
{
    servers {
        protocols h1 h2
    }
}

yourdomain.com {
    rate_limit {
        zone static_ip {
            key {remote_host}
            events 100
            window 1m
        }
    }
    # ... rest of config
}
```

#### DDoS Protection
For additional DDoS protection, use:
- **Cloudflare**: CDN with DDoS protection
- **AWS Shield**: If using AWS
- **Fail2ban**: Application-level rate limiting

#### IP Allowlisting (Optional)
For highly sensitive deployments:
```yaml
# In firewall configuration
firewall_rules:
  - rule: allow
    from_ip: "TRUSTED_IP_RANGE"
    port: "443"
    proto: tcp
```

## Access Control

### Authelia Access Rules

#### Basic Access Control
```yaml
# In configuration.yml.j2
access_control:
  default_policy: deny
  rules:
    # Public access to auth portal
    - domain: "auth.{{ domain_name }}"
      policy: bypass
    
    # Admin-only services
    - domain: "prometheus.{{ domain_name }}"
      policy: two_factor
      subject: "group:admins"
    
    # All authenticated users
    - domain: "grafana.{{ domain_name }}"
      policy: two_factor
```

#### Advanced Access Control
```yaml
# Network-based restrictions
access_control:
  rules:
    # Allow admin from specific network
    - domain: "prometheus.{{ domain_name }}"
      policy: two_factor
      subject: "group:admins"
      networks:
        - "192.168.1.0/24"
        - "10.0.0.0/8"
    
    # Time-based restrictions
    - domain: "admin.{{ domain_name }}"
      policy: two_factor
      subject: "group:admins"
      methods: ["GET", "POST"]
```

### User Groups and Permissions
```yaml
# In users_database.yml.j2
groups:
  - name: admins
    description: "Full system access"
  
  - name: operators
    description: "Monitoring and logs access"
  
  - name: viewers
    description: "Read-only access to dashboards"

users:
  admin:
    groups: ["admins"]
  
  operator:
    groups: ["operators"]
  
  viewer:
    groups: ["viewers"]
```

## SSL/TLS Security

### Certificate Management

#### Certificate Security
- **Automatic Renewal**: Caddy handles renewal automatically
- **Strong Ciphers**: Modern TLS configuration
- **Perfect Forward Secrecy**: Ephemeral key exchange
- **OCSP Stapling**: Certificate status checking

**Check Certificate Security**:
```bash
# Test SSL configuration
curl -I https://yourdomain.com

# Check certificate details
echo | openssl s_client -connect yourdomain.com:443 -servername yourdomain.com 2>/dev/null | openssl x509 -noout -text

# Test SSL security (using online tools)
# ssllabs.com/ssltest/
```

#### Custom Certificate Configuration
For specific security requirements:
```caddy
# In Caddyfile
{
    servers {
        protocols h2 h1
        strict_sni_host on
    }
}

yourdomain.com {
    tls {
        protocols tls1.2 tls1.3
        ciphers TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384 TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
    }
    # ... rest of config
}
```

### Security Headers
Caddy automatically includes security headers:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

## Monitoring and Alerting

### Security Monitoring

#### Log Analysis
```bash
# Authentication failures
just logs authelia | grep -i "authentication failed"

# SSH attack attempts
just ssh "sudo grep 'Failed password' /var/log/auth.log"

# Unusual network activity
just ssh "sudo netstat -an | grep LISTEN"

# Process monitoring
just ssh "ps aux --sort=-%cpu | head -10"
```

#### Automated Security Alerts
Set up alerts for security events:
```yaml
# In prometheus alert rules
- alert: HighAuthenticationFailures
  expr: increase(authelia_authentication_failed_total[5m]) > 10
  for: 0m
  labels:
    severity: warning
  annotations:
    summary: "High authentication failure rate"

- alert: SuspiciousNetworkActivity
  expr: rate(node_network_receive_bytes_total[5m]) > 50000000
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Unusual network traffic detected"
```

#### Security Dashboards
Monitor security metrics in Grafana:
- Failed authentication attempts over time
- Banned IPs from fail2ban
- SSL certificate expiration dates
- System login attempts
- Network traffic patterns

### Intrusion Detection

#### File Integrity Monitoring
```bash
# Install AIDE (Advanced Intrusion Detection Environment)
just ssh "sudo apt install aide -y"

# Initialize database
just ssh "sudo aide --init"
just ssh "sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db"

# Run integrity check
just ssh "sudo aide --check"
```

#### Network Monitoring
```bash
# Monitor network connections
just ssh "sudo netstat -tuln"

# Check for unusual processes
just ssh "sudo ps aux | grep -v '\['"

# Monitor system calls (if needed)
just ssh "sudo strace -p PID"
```

## Incident Response

### Security Incident Procedures

#### Immediate Response
1. **Identify Threat**: Analyze logs and system state
2. **Contain**: Isolate affected systems
3. **Eradicate**: Remove threat and vulnerabilities
4. **Recover**: Restore services securely
5. **Document**: Record incident details

#### Emergency Commands
```bash
# Block suspicious IP immediately
just ssh "sudo ufw deny from SUSPICIOUS_IP"

# Stop all services (emergency)
just ssh "docker stop \$(docker ps -q)"

# Disconnect from network (extreme measure)
just ssh "sudo ifconfig eth0 down"

# Enable emergency SSH access
just ssh "sudo ufw allow 22"
```

#### Investigation Tools
```bash
# Recent logins
just ssh "sudo last | head -20"

# Current active sessions
just ssh "sudo who"

# Process tree
just ssh "sudo pstree"

# Network connections
just ssh "sudo ss -tuln"

# System logs
just ssh "sudo journalctl --since '1 hour ago' | grep -i error"
```

### Forensics and Recovery

#### Evidence Collection
```bash
# System state snapshot
just ssh "sudo tar -czf /tmp/forensic-snapshot-\$(date +%Y%m%d_%H%M%S).tar.gz /var/log/ /etc/ /opt/"

# Memory dump (if available)
just ssh "sudo dd if=/dev/mem of=/tmp/memory-dump.img"

# Network state
just ssh "sudo ss -tuln > /tmp/network-state.txt"
```

#### Recovery Procedures
```bash
# Reset to known good state
git checkout KNOWN_GOOD_COMMIT
just deploy

# Restore from backup
just ssh "sudo tar -xzf /backup/system-backup.tar.gz -C /"

# Reset authentication (if compromised)
just reset-authelia-bans
just deploy-authelia
```

## Security Maintenance

### Regular Security Tasks

#### Weekly Tasks
```bash
# Security log review
just logs authelia | grep -i "failed\|error" | tail -50
just ssh "sudo grep 'authentication failure' /var/log/auth.log | tail -20"

# System update check
just ssh "sudo apt list --upgradable"

# Certificate expiration check
echo | openssl s_client -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates

# Backup verification
ls -la backups/ | tail -10
```

#### Monthly Tasks
```bash
# User access review
just ssh "cat /opt/authelia/config/users_database.yml"

# SSH key rotation (if policy requires)
ssh-keygen -t ed25519 -C "monthly-rotation-$(date +%Y%m)"

# Security configuration audit
just validate-full
just health-check

# Vulnerability scanning (using external tools)
# nmap, OpenVAS, or cloud security scanners
```

#### Quarterly Tasks
```bash
# Comprehensive security audit
# Review all configurations
# Update security documentation
# Test incident response procedures
# Review and update access controls

# Penetration testing (recommended)
# External security assessment
# Social engineering awareness
```

### Security Updates

#### Staying Current
```bash
# Monitor security advisories
# - Ubuntu Security Notices
# - Docker Security Updates
# - Application CVE databases

# Update process
just validate-full
just test-local
just deploy

# Post-update verification
just health-check
```

### Security Tools Integration

#### External Security Services
- **Vulnerability Scanners**: Nessus, OpenVAS, Qualys
- **SIEM Integration**: Splunk, ELK Stack, Sumo Logic
- **Cloud Security**: AWS Security Hub, Azure Security Center
- **DNS Security**: Cloudflare, Quad9

#### Compliance Frameworks
Consider alignment with:
- **CIS Controls**: Center for Internet Security benchmarks
- **NIST Cybersecurity Framework**: Risk management framework
- **ISO 27001**: Information security management
- **SOC 2**: Service organization controls

This security guide provides comprehensive protection for your VPS configuration. Regular implementation of these security measures will maintain a robust security posture.