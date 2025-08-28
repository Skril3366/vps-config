# Configuration Guide

This comprehensive guide covers all configuration options, files, and variables for the VPS setup.

## Table of Contents
- [Configuration Overview](#configuration-overview)
- [Inventory Configuration](#inventory-configuration)
- [Global Variables](#global-variables)
- [Service Configuration](#service-configuration)
- [Authelia Configuration](#authelia-configuration)
- [Environment Variables](#environment-variables)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Security Configuration](#security-configuration)
- [Monitoring Configuration](#monitoring-configuration)

## Configuration Overview

The VPS configuration uses a hierarchical approach:

```
Priority (High to Low):
1. Command-line variables (-e key=value)
2. Host variables (host_vars/hostname.yml)
3. Group variables (group_vars/all.yml)
4. Role defaults (roles/*/defaults/main.yml)
5. Environment files (.env)
```

## Inventory Configuration

### Production Inventory (`ansible/inventories/production.yml`)

```yaml
---
all:
  hosts:
    vps:
      # Connection settings
      ansible_host: "192.168.1.100"          # Your VPS IP address
      ansible_user: "ubuntu"                 # SSH user with sudo access
      ansible_ssh_private_key_file: "~/.ssh/vps_key"  # Path to SSH private key
      ansible_become: yes                     # Enable privilege escalation
      ansible_become_method: sudo             # Use sudo for privilege escalation
      
      # Python interpreter (usually auto-detected)
      ansible_python_interpreter: "/usr/bin/python3"
  
  vars:
    # Domain configuration (REQUIRED)
    domain_name: "example.com"              # Your primary domain
    letsencrypt_email: "admin@example.com"  # Email for Let's Encrypt certificates
    
    # SSH configuration
    ssh_port: 22                            # SSH port (change for security)
    
    # Optional: Override default service ports
    authelia_port: 9091
    grafana_port: 3000
    prometheus_port: 9090
    loki_port: 3100
    
    # Optional: Custom Docker image versions
    caddy_image: "caddy:2.7-alpine"
    authelia_image: "authelia/authelia:4.38"
```

### Host-Specific Variables

For multiple servers, create host-specific variable files:

```bash
# Create host variable directory
mkdir -p ansible/host_vars/vps

# Edit host-specific variables
vim ansible/host_vars/vps/main.yml
```

Example `ansible/host_vars/vps/main.yml`:
```yaml
---
# VPS-specific configuration
system_timezone: "America/New_York"
prometheus_retention_time: "30d"

# Custom resource limits
grafana_memory_limit: "512m"
prometheus_memory_limit: "1g"

# Additional monitoring targets
additional_prometheus_targets:
  - "192.168.1.50:9100"  # Additional server
  - "192.168.1.51:3000"  # Application endpoint
```

## Global Variables

### Main Configuration (`ansible/group_vars/all.yml`)

```yaml
---
# System Configuration
system_timezone: "UTC"                    # Server timezone
apt_cache_valid_time: 3600               # APT cache validity (seconds)

# Directory Structure
base_directory: "/opt"                   # Base directory for all services
logs_directory: "/opt/logs"              # Centralized log directory

# Service Directories
caddy_directory: "/opt/caddy"
caddy_config_directory: "/opt/caddy/config"
caddy_data_directory: "/opt/caddy/data"
prometheus_directory: "/opt/prometheus"
grafana_data_directory: "/opt/grafana/data"
grafana_provisioning_directory: "/opt/grafana/provisioning"
grafana_dashboards_directory: "/opt/grafana/dashboards"
loki_directory: "/opt/loki"
promtail_directory: "/opt/promtail"
authelia_directory: "/opt/authelia"
authelia_config_directory: "/opt/authelia/config"
authelia_data_directory: "/opt/authelia/data"

# Docker Images and Versions
caddy_image: "caddy:2-alpine"
authelia_image: "authelia/authelia:latest"
node_exporter_image: "prom/node-exporter:latest"
prometheus_image: "prom/prometheus:latest"
grafana_image: "grafana/grafana:latest"
loki_image: "grafana/loki:latest"
promtail_image: "grafana/promtail:latest"
cadvisor_image: "gcr.io/cadvisor/cadvisor:latest"

# Network Configuration
http_port: 80
https_port: 443
node_exporter_port: 9100

# Service Ports (customizable per environment)
authelia_port: 9091
grafana_port: 3000
prometheus_port: 9090
loki_port: 3100

# SSH Configuration
ssh_port: 22
ssh_permit_root_login: "no"              # Disable root login
ssh_password_authentication: "no"        # Require key authentication
ssh_pubkey_authentication: "yes"
ssh_max_auth_tries: 3                    # Limit authentication attempts
ssh_client_alive_interval: 300           # Keep connections alive
ssh_client_alive_count_max: 2

# Security Configuration
fail2ban_enabled: true                   # Enable intrusion detection
unattended_upgrades_enabled: true        # Automatic security updates
automatic_reboot: false                  # Automatic reboot for kernel updates

# Monitoring Configuration
prometheus_retention_time: "15d"         # Metrics retention period
grafana_admin_password: "admin"          # Default Grafana admin password (change!)

# Authelia Configuration
authelia_domain: "auth.{{ domain_name }}"
session_domain: "{{ domain_name }}"

# Package Lists
essential_packages:
  - curl
  - wget
  - git
  - htop
  - unzip
  - vim
  - tree
  - software-properties-common
  - apt-transport-https
  - ca-certificates
  - gnupg
  - lsb-release

docker_packages:
  - docker-ce
  - docker-ce-cli
  - containerd.io
  - docker-compose-plugin

security_packages:
  - fail2ban
  - unattended-upgrades
  - ufw
```

## Service Configuration

### Caddy Configuration

The Caddy reverse proxy is configured through `ansible/roles/caddy/templates/Caddyfile.j2`:

```caddy
# Global options
{
    email {{ letsencrypt_email }}
    admin off
}

# Main domain redirect
{{ domain_name }} {
    redir https://auth.{{ domain_name }}
}

# Authentication portal
auth.{{ domain_name }} {
    reverse_proxy authelia:{{ authelia_port }}
    
    log {
        output file /var/log/caddy/auth.log {
            roll_size 10mb
            roll_keep 3
        }
    }
}

# Protected services with forward auth
grafana.{{ domain_name }} {
    forward_auth authelia:{{ authelia_port }} {
        uri /api/verify?rd=https://auth.{{ domain_name }}/
        copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
    }
    
    reverse_proxy grafana:{{ grafana_port }}
    
    log {
        output file /var/log/caddy/grafana.log
    }
}

prometheus.{{ domain_name }} {
    forward_auth authelia:{{ authelia_port }} {
        uri /api/verify?rd=https://auth.{{ domain_name }}/
        copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
    }
    
    reverse_proxy prometheus:{{ prometheus_port }}
}

loki.{{ domain_name }} {
    forward_auth authelia:{{ authelia_port }} {
        uri /api/verify?rd=https://auth.{{ domain_name }}/
        copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
    }
    
    reverse_proxy loki:{{ loki_port }}
}

# Custom applications (add your own here)
# app.{{ domain_name }} {
#     forward_auth authelia:{{ authelia_port }} {
#         uri /api/verify?rd=https://auth.{{ domain_name }}/
#     }
#     reverse_proxy your-app:port
# }
```

### Adding Custom Applications

To add your own applications behind authentication:

1. **Add Docker service** to your compose file
2. **Add Caddy configuration** in the Caddyfile template:
   ```caddy
   myapp.{{ domain_name }} {
       forward_auth authelia:{{ authelia_port }} {
           uri /api/verify?rd=https://auth.{{ domain_name }}/
           copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
       }
       reverse_proxy myapp:3000
   }
   ```
3. **Add DNS record** pointing to your VPS
4. **Redeploy** with `just deploy`

## Authelia Configuration

Authelia is the most complex service to configure due to its security requirements.

### Main Configuration (`ansible/roles/authelia/templates/configuration.yml.j2`)

```yaml
---
server:
  host: 0.0.0.0
  port: {{ authelia_port }}
  path: ""
  enable_pprof: false
  enable_expvars: false

log:
  level: info
  format: text

jwt_secret: "{{ authelia_jwt_secret }}"
default_redirection_url: "https://{{ domain_name }}"

authentication_backend:
  file:
    path: /config/users_database.yml
    password:
      algorithm: argon2id
      iterations: 3
      memory: 65536
      parallelism: 4
      key_length: 32
      salt_length: 16

access_control:
  default_policy: deny
  rules:
    # Allow access to auth portal itself
    - domain: "auth.{{ domain_name }}"
      policy: bypass
    
    # Require authentication for all subdomains
    - domain: "*.{{ domain_name }}"
      policy: two_factor

session:
  name: authelia_session
  domain: "{{ domain_name }}"
  secret: "{{ authelia_session_secret }}"
  expiration: 1h
  inactivity: 5m
  remember_me_duration: 1M

  redis:
    host: redis
    port: 6379
    username: ""
    password: ""
    database_index: 0
    maximum_active_connections: 8
    minimum_idle_connections: 0

regulation:
  max_retries: 10
  find_time: 2m
  ban_time: 5m

storage:
  encryption_key: "{{ authelia_storage_encryption_key }}"
  local:
    path: /data/db.sqlite3

notifier:
  disable_startup_check: false
  {% if authelia_smtp_host is defined %}
  smtp:
    host: "{{ authelia_smtp_host }}"
    port: {{ authelia_smtp_port | default(587) }}
    timeout: 5s
    username: "{{ authelia_smtp_username }}"
    password: "{{ authelia_smtp_password }}"
    sender: "{{ authelia_sender | default('noreply@' + domain_name) }}"
    identifier: localhost
    subject: "[Authelia] {title}"
    startup_check_address: "{{ authelia_admin_email }}"
    disable_require_tls: false
    disable_html_emails: false
  {% else %}
  filesystem:
    filename: /data/notification.txt
  {% endif %}
```

### User Database (`ansible/roles/authelia/templates/users_database.yml.j2`)

```yaml
---
users:
  {{ authelia_admin_user }}:
    displayname: "{{ authelia_admin_displayname }}"
    password: "{{ authelia_admin_password_hash }}"
    email: "{{ authelia_admin_email }}"
    groups:
      - admins
      - dev

  # Add additional users here
  # user2:
  #   displayname: "User Two"
  #   password: "$argon2id$v=19$m=65536,t=3,p=4$..."
  #   email: "user2@example.com"
  #   groups:
  #     - users

groups:
  - name: admins
    description: "Administrators with full access"
  
  - name: dev
    description: "Developers with monitoring access"
  
  - name: users
    description: "Regular users with limited access"
```

## Environment Variables

### Authelia Environment File (`ansible/inventories/production/.env`)

```bash
# Authentication Secrets (REQUIRED - Generate with openssl rand -base64 32)
AUTHELIA_JWT_SECRET="your_generated_jwt_secret_here"
AUTHELIA_SESSION_SECRET="your_generated_session_secret_here"
AUTHELIA_STORAGE_ENCRYPTION_KEY="your_generated_storage_key_here"

# Admin User Configuration
AUTHELIA_ADMIN_USER=admin
AUTHELIA_ADMIN_DISPLAYNAME=Administrator
AUTHELIA_ADMIN_EMAIL=admin@yourdomain.com

# Admin Password Hash (Generate with: just authelia-hash 'yourpassword')
# IMPORTANT: NO QUOTES around the hash value
AUTHELIA_ADMIN_PASSWORD_HASH=$argon2id$v=19$m=65536,t=3,p=4$abcdefghijklmnopqrstuvwxyz123456$longhashstringhere

# SMTP Configuration (Optional - for password reset emails)
AUTHELIA_SMTP_HOST=smtp.gmail.com
AUTHELIA_SMTP_PORT=587
AUTHELIA_SMTP_USERNAME=your-email@gmail.com
AUTHELIA_SMTP_PASSWORD=your-app-specific-password
AUTHELIA_SENDER=noreply@yourdomain.com

# Redis Configuration (Usually defaults are fine)
# REDIS_PASSWORD=optional_redis_password

# Additional Authelia Settings
# AUTHELIA_LOG_LEVEL=info
# AUTHELIA_LOG_FORMAT=text
```

**Security Notes**:
- Environment file permissions are automatically set to 0600 (owner read/write only)
- Never commit this file to version control
- Generate strong random secrets (minimum 32 characters)
- Use app-specific passwords for SMTP, not your main email password

## SSL/TLS Configuration

### Automatic HTTPS with Let's Encrypt

Caddy automatically obtains SSL certificates from Let's Encrypt. Configuration:

```yaml
# In group_vars/all.yml or inventory
letsencrypt_email: "admin@yourdomain.com"  # REQUIRED for certificate issuance
```

### Certificate Storage

Certificates are automatically stored in:
- **Location**: `/opt/caddy/data/caddy/certificates/`
- **Renewal**: Automatic (30 days before expiration)
- **Backup**: Include in regular backups

### Custom SSL Configuration

For custom certificates or CA:

```caddy
# In Caddyfile template
{
    cert_file /path/to/cert.pem
    key_file /path/to/key.pem
}
```

## Security Configuration

### SSH Hardening

SSH configuration is managed in the security role:

```yaml
# In group_vars/all.yml
ssh_port: 22                      # Change for security through obscurity
ssh_permit_root_login: "no"       # Disable root login
ssh_password_authentication: "no" # Require key authentication
ssh_pubkey_authentication: "yes"
ssh_max_auth_tries: 3
ssh_client_alive_interval: 300
ssh_client_alive_count_max: 2

# Additional SSH settings
ssh_allow_users:                  # Limit SSH access to specific users
  - "ubuntu"
  - "admin"

ssh_deny_users:                   # Explicitly deny users
  - "root"
  - "git"
```

### Firewall Configuration

UFW (Uncomplicated Firewall) rules:

```yaml
# In security role variables
firewall_rules:
  - rule: allow
    port: "{{ ssh_port }}"
    proto: tcp
  
  - rule: allow
    port: "80"
    proto: tcp
  
  - rule: allow
    port: "443"
    proto: tcp

# Deny all other traffic by default
firewall_default_policy: deny
```

### Fail2ban Configuration

Intrusion detection and prevention:

```yaml
# In group_vars/all.yml
fail2ban_enabled: true

# Jail configurations
fail2ban_jails:
  sshd:
    enabled: true
    port: "{{ ssh_port }}"
    filter: sshd
    logpath: /var/log/auth.log
    maxretry: 5
    findtime: 600
    bantime: 3600
  
  caddy:
    enabled: true
    port: "80,443"
    filter: caddy
    logpath: /var/log/caddy/*.log
    maxretry: 10
    findtime: 600
    bantime: 1800
```

## Monitoring Configuration

### Prometheus Configuration

Metrics collection targets and rules:

```yaml
# In ansible/roles/monitoring/templates/prometheus.yml.j2
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  # Node Exporter (system metrics)
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 15s
    metrics_path: /metrics

  # cAdvisor (container metrics)
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
    scrape_interval: 30s

  # Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Caddy metrics (if enabled)
  - job_name: 'caddy'
    static_configs:
      - targets: ['caddy:2019']
    metrics_path: /metrics
    scrape_interval: 30s

  # Custom application targets
  {% if additional_prometheus_targets is defined %}
  - job_name: 'additional-targets'
    static_configs:
      - targets: {{ additional_prometheus_targets | to_json }}
  {% endif %}

alerting:
  alertmanagers:
    - static_configs:
        - targets: []
```

### Grafana Configuration

Dashboard and datasource provisioning:

```yaml
# In datasources.yml.j2
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:{{ prometheus_port }}
    isDefault: true
    editable: true

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:{{ loki_port }}
    editable: true
    jsonData:
      maxLines: 1000
```

### Loki Configuration

Log aggregation setup:

```yaml
# In loki.yml.j2
auth_enabled: false

server:
  http_listen_port: {{ loki_port }}

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb:
    directory: /loki/index

  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
```

### Custom Monitoring

To add custom metrics:

1. **Add scrape target** to Prometheus configuration
2. **Create custom dashboard** in Grafana
3. **Add alerting rules** for critical metrics

Example custom target:
```yaml
# In host_vars or group_vars
additional_prometheus_targets:
  - "myapp:8080"
  - "database:9187"
```

This comprehensive configuration guide covers all major aspects of the VPS setup. For specific service configurations, refer to the individual template files in each Ansible role.