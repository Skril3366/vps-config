# Service Documentation

This document provides detailed information about each service in the VPS configuration, including their purpose, configuration, endpoints, and management.

## Table of Contents
- [Service Overview](#service-overview)
- [Caddy (Reverse Proxy)](#caddy-reverse-proxy)
- [Authelia (Authentication)](#authelia-authentication)
- [Prometheus (Metrics)](#prometheus-metrics)
- [Grafana (Dashboards)](#grafana-dashboards)
- [Loki (Log Aggregation)](#loki-log-aggregation)
- [Supporting Services](#supporting-services)
- [Service Dependencies](#service-dependencies)
- [Port Reference](#port-reference)

## Service Overview

The VPS setup consists of the following core services:

| Service | Purpose | Port | Authentication Required | Exposed Domain |
|---------|---------|------|------------------------|-----------------|
| Caddy | Reverse proxy & SSL termination | 80/443 | No | yourdomain.com |
| Authelia | Authentication & 2FA | 9091 | No (auth portal) | auth.yourdomain.com |
| Grafana | Metrics visualization | 3000 | Yes | grafana.yourdomain.com |
| Prometheus | Metrics collection | 9090 | Yes | prometheus.yourdomain.com |
| Loki | Log aggregation | 3100 | Yes | loki.yourdomain.com |
| Node Exporter | System metrics | 9100 | No | Direct IP access only |
| Redis | Session storage | 6379 | No | Internal only |
| Promtail | Log collection | 9080 | No | Internal only |

## Caddy (Reverse Proxy)

### Purpose
Caddy serves as the entry point for all HTTP/HTTPS traffic, providing:
- Automatic HTTPS with Let's Encrypt certificates
- Reverse proxy functionality
- Forward authentication integration
- HTTP to HTTPS redirection

### Configuration Files
- **Primary Config**: `/opt/caddy/Caddyfile`
- **Template**: `ansible/roles/caddy/templates/Caddyfile.j2`
- **SSL Certificates**: `/opt/caddy/data/caddy/certificates/`

### Key Features
```caddy
# Automatic HTTPS with Let's Encrypt
{
    email admin@yourdomain.com
    admin off
}

# Forward authentication for protected services
grafana.yourdomain.com {
    forward_auth authelia:9091 {
        uri /api/verify?rd=https://auth.yourdomain.com/
        copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
    }
    reverse_proxy grafana:3000
}
```

### Management Commands
```bash
# Restart Caddy service
just restart caddy

# View Caddy logs
just logs caddy

# Reload configuration without restart
just ssh "docker exec caddy caddy reload --config /etc/caddy/Caddyfile"

# Check configuration syntax
just ssh "docker exec caddy caddy validate --config /etc/caddy/Caddyfile"

# View certificate status
just ssh "docker exec caddy caddy list-certificates"

# Manual certificate renewal
just ssh "docker exec caddy caddy reload"
```

### SSL Certificate Management
```bash
# Check certificate expiration
echo | openssl s_client -connect yourdomain.com:443 -servername yourdomain.com 2>/dev/null | openssl x509 -noout -dates

# View certificate details
just ssh "docker exec caddy cat /data/caddy/certificates/acme-v02.api.letsencrypt.org-directory/yourdomain.com/yourdomain.com.crt | openssl x509 -noout -text"

# Certificate storage location
just ssh "ls -la /opt/caddy/data/caddy/certificates/"
```

### Adding New Services
To add a new service behind Caddy:

1. **Add to Caddyfile template**:
```caddy
myapp.yourdomain.com {
    forward_auth authelia:9091 {
        uri /api/verify?rd=https://auth.yourdomain.com/
    }
    reverse_proxy myapp:8080
}
```

2. **Update DNS**: Add A record for `myapp.yourdomain.com`
3. **Redeploy**: Run `just update-caddy` or `just deploy`

## Authelia (Authentication)

### Purpose
Authelia provides centralized authentication and authorization with:
- Multi-factor authentication (TOTP/2FA)
- Session management with Redis
- User database with groups and permissions
- Forward authentication for reverse proxies

### Configuration Files
- **Main Config**: `/opt/authelia/config/configuration.yml`
- **Users Database**: `/opt/authelia/config/users_database.yml`
- **Environment**: `/opt/authelia/.env`
- **Data**: `/opt/authelia/data/` (SQLite database, TOTP secrets)

### Authentication Flow
```
1. User visits protected service (e.g., grafana.example.com)
2. Caddy checks with Authelia (/api/verify endpoint)
3. If not authenticated, user redirected to auth.example.com
4. User enters credentials (username/password + TOTP)
5. Authelia creates session, stores in Redis
6. User redirected back to original service
7. Subsequent requests use session cookie
```

### User Management
```bash
# Generate password hash for new user
just authelia-hash 'user-password'

# Reset user 2FA (requires manual database edit)
just ssh "sqlite3 /opt/authelia/data/db.sqlite3 'DELETE FROM totp_configurations WHERE username=\"username\";'"

# Clear user bans and regulation
just reset-authelia-bans

# View user database
just ssh "cat /opt/authelia/config/users_database.yml"
```

### Session Management
```bash
# View active sessions
just ssh "docker exec redis redis-cli KEYS 'authelia:*'"

# Clear all sessions
just ssh "docker exec redis redis-cli FLUSHALL"

# Check session configuration
just logs authelia | grep -i session

# Test Redis connectivity
just ssh "docker exec authelia redis-cli -h redis ping"
```

### Access Control Rules
```yaml
# In configuration.yml
access_control:
  default_policy: deny
  rules:
    # Allow auth portal itself
    - domain: "auth.example.com"
      policy: bypass
    
    # Admin-only services
    - domain: "admin.example.com"
      policy: two_factor
      subject: "group:admins"
    
    # All authenticated users
    - domain: "*.example.com"
      policy: two_factor
```

### Management Commands
```bash
# Restart Authelia
just restart authelia

# View logs with authentication details
just logs authelia | grep -i "authentication\|login\|failed"

# Deploy only Authelia (after config changes)
just deploy-authelia

# Check configuration
just ssh "docker exec authelia authelia validate --config /config/configuration.yml"
```

## Prometheus (Metrics)

### Purpose
Prometheus collects and stores time-series metrics from various sources:
- System metrics (CPU, memory, disk, network)
- Container metrics (Docker stats)
- Application metrics (custom exporters)
- Service health monitoring

### Configuration Files
- **Main Config**: `/opt/prometheus/prometheus.yml`
- **Alert Rules**: `/opt/prometheus/alert_rules.yml`
- **Data**: `/opt/prometheus/data/` (TSDB storage)

### Scrape Targets
```yaml
scrape_configs:
  # System metrics
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 15s

  # Container metrics
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### Key Metrics
```bash
# System metrics examples
up                                    # Service availability
node_cpu_seconds_total               # CPU usage
node_memory_MemAvailable_bytes       # Available memory
node_filesystem_free_bytes           # Disk space
node_load1                          # System load

# Container metrics
container_cpu_usage_seconds_total    # Container CPU
container_memory_usage_bytes         # Container memory
container_fs_usage_bytes            # Container disk usage
```

### Management Commands
```bash
# Restart Prometheus
just restart prometheus

# Check target status
curl -s http://localhost:9090/api/v1/targets

# Query metrics via API
curl 'http://localhost:9090/api/v1/query?query=up'

# Check configuration
curl -s http://localhost:9090/api/v1/status/config

# View storage usage
just ssh "du -sh /opt/prometheus/data/"

# Reload configuration
just ssh "docker exec prometheus kill -HUP 1"
```

### Custom Queries
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

## Grafana (Dashboards)

### Purpose
Grafana provides visualization and dashboards for:
- System performance monitoring
- Container resource usage
- Log analysis and visualization
- Custom application metrics

### Configuration Files
- **Data**: `/opt/grafana/data/`
- **Dashboards**: `/opt/grafana/dashboards/`
- **Provisioning**: `/opt/grafana/provisioning/`

### Pre-configured Dashboards

#### System Overview Dashboard
- **CPU Usage**: Multi-core CPU utilization
- **Memory Usage**: RAM and swap usage
- **Disk Usage**: Filesystem usage and I/O
- **Network**: Traffic and connectivity
- **Load Average**: System load over time

#### Docker Overview Dashboard
- **Container Status**: Running/stopped containers
- **Resource Usage**: CPU and memory per container
- **Network**: Container network traffic
- **Storage**: Container filesystem usage

#### Logs Overview Dashboard
- **Log Volume**: Logs per service over time
- **Error Rates**: Error and warning counts
- **Top Services**: Most active log sources
- **Recent Events**: Latest log entries

### Management Commands
```bash
# Restart Grafana
just restart grafana

# Reset admin password
just ssh "docker exec grafana grafana-cli admin reset-admin-password newpassword"

# View logs
just logs grafana

# Backup dashboards
just ssh "cp -r /opt/grafana/data/dashboards/ /backup/"

# Import dashboard from JSON
# Use Grafana UI: Dashboard → Import
```

### Datasource Configuration
```yaml
# Prometheus datasource
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
```

### Custom Dashboard Creation
1. **Access Grafana**: https://grafana.yourdomain.com
2. **Create Dashboard**: Plus icon → Dashboard
3. **Add Panel**: Add new panel
4. **Configure Query**: Select Prometheus datasource, enter PromQL
5. **Customize Visualization**: Choose graph type, colors, etc.
6. **Save Dashboard**: Save with descriptive name

## Loki (Log Aggregation)

### Purpose
Loki aggregates logs from various sources:
- Container logs (via Promtail)
- System logs (/var/log)
- Application logs
- Structured log analysis

### Configuration Files
- **Main Config**: `/opt/loki/loki.yml`
- **Data**: `/opt/loki/data/` (Index and chunks)

### Log Sources
```yaml
# Promtail configuration
scrape_configs:
  # Docker container logs
  - job_name: containers
    static_configs:
      - targets: [localhost]
        labels:
          job: containerlogs
          __path__: /var/lib/docker/containers/*/*log

  # System logs
  - job_name: syslog
    static_configs:
      - targets: [localhost]
        labels:
          job: syslog
          __path__: /var/log/*.log
```

### Log Queries (LogQL)
```bash
# All logs from a specific service
{job="containerlogs", container_name="grafana"}

# Error logs across all services
{job="containerlogs"} |= "error" or "ERROR"

# Authentication failures
{job="containerlogs", container_name="authelia"} |= "failed"

# Rate of log entries
rate({job="containerlogs"}[5m])

# Filter by time range
{job="containerlogs"} | json | timestamp > 1h
```

### Management Commands
```bash
# Restart Loki
just restart loki

# Check log ingestion
curl -s 'http://localhost:3100/loki/api/v1/labels'

# Query logs via API
curl -s 'http://localhost:3100/loki/api/v1/query_range?query={job="containerlogs"}&limit=10'

# Check storage usage
just ssh "du -sh /opt/loki/data/"

# View recent logs
curl 'http://localhost:3100/loki/api/v1/query_range?query={job="containerlogs"}&start=1h'
```

## Supporting Services

### Redis (Session Storage)
**Purpose**: Session storage for Authelia
```bash
# Check Redis status
just ssh "docker exec redis redis-cli ping"

# View session keys
just ssh "docker exec redis redis-cli KEYS '*'"

# Monitor Redis activity
just ssh "docker exec redis redis-cli MONITOR"
```

### Node Exporter (System Metrics)
**Purpose**: Exposes system metrics for Prometheus
```bash
# Check metrics endpoint
curl http://localhost:9100/metrics

# View specific metrics
curl -s http://localhost:9100/metrics | grep node_cpu
```

### Promtail (Log Collection)
**Purpose**: Collects logs and sends to Loki
```bash
# Check Promtail status
just logs promtail

# View configuration
just ssh "cat /opt/promtail/config.yml"

# Test connectivity to Loki
just ssh "docker exec promtail wget -qO- http://loki:3100/ready"
```

### cAdvisor (Container Metrics)
**Purpose**: Exposes container resource metrics
```bash
# Check container metrics
curl http://localhost:8080/metrics

# View container stats
curl http://localhost:8080/api/v1.3/containers/
```

## Service Dependencies

### Startup Order
```
1. Redis (session storage)
2. Authelia (depends on Redis)
3. Prometheus, Loki (independent services)  
4. Grafana (depends on Prometheus, Loki)
5. Caddy (depends on all backend services)
6. Supporting services (Node Exporter, Promtail, cAdvisor)
```

### Service Communication
```
Caddy → Authelia (authentication)
Caddy → Grafana, Prometheus, Loki (reverse proxy)
Authelia → Redis (session storage)
Grafana → Prometheus, Loki (data sources)
Promtail → Loki (log shipping)
Prometheus → Node Exporter, cAdvisor (metric scraping)
```

### Network Dependencies
All services communicate through the `vps-config_default` Docker network:
```bash
# View network configuration
just ssh "docker network inspect vps-config_default"

# Test inter-service connectivity
just ssh "docker exec caddy ping authelia"
just ssh "docker exec grafana wget -qO- http://prometheus:9090/api/v1/query?query=up"
```

## Port Reference

### External Ports (Internet-accessible)
| Port | Service | Purpose | Notes |
|------|---------|---------|--------|
| 80 | Caddy | HTTP (redirects to HTTPS) | Public |
| 443 | Caddy | HTTPS | Public |
| 22 | SSH | System access | Configurable |

### Internal Ports (Docker network only)
| Port | Service | Purpose | Accessible via |
|------|---------|---------|----------------|
| 9091 | Authelia | Authentication | auth.domain.com |
| 3000 | Grafana | Dashboards | grafana.domain.com |
| 9090 | Prometheus | Metrics | prometheus.domain.com |
| 3100 | Loki | Logs | loki.domain.com |
| 9100 | Node Exporter | System metrics | IP:9100 (direct) |
| 6379 | Redis | Session storage | Internal only |
| 9080 | Promtail | Log collection | Internal only |
| 8080 | cAdvisor | Container metrics | Internal only |

### Service Health Endpoints
```bash
# Check all service health
curl -s https://auth.yourdomain.com/api/health
curl -s https://grafana.yourdomain.com/api/health
curl -s http://YOUR_VPS_IP:9090/-/healthy
curl -s http://YOUR_VPS_IP:3100/ready
curl -s http://YOUR_VPS_IP:9100/
```

This service documentation provides comprehensive information for managing and troubleshooting each component of the VPS setup. For specific configuration changes, refer to the [Configuration Guide](configuration.md).