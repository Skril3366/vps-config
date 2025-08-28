# Customization Guide

This guide covers how to extend and customize the VPS configuration to add your own services, modify existing configurations, and adapt the setup to your specific needs.

## Table of Contents
- [Adding New Services](#adding-new-services)
- [Modifying Existing Services](#modifying-existing-services)
- [Custom Dashboards and Monitoring](#custom-dashboards-and-monitoring)
- [Advanced Configuration](#advanced-configuration)
- [Development Workflow](#development-workflow)
- [Best Practices](#best-practices)

## Adding New Services

### Basic Service Addition

#### 1. Create Docker Service Definition
Create or edit `docker/compose/custom.yml`:

```yaml
version: '3.8'

services:
  myapp:
    image: nginx:alpine
    container_name: myapp
    ports:
      - "8080:80"
    volumes:
      - ./app:/usr/share/nginx/html:ro
    networks:
      - vps-config_default
    restart: unless-stopped
    labels:
      - "traefik.enable=false"  # We use Caddy, not Traefik

  # Database example
  postgres:
    image: postgres:15
    container_name: postgres
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: securepassword
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - vps-config_default
    restart: unless-stopped

volumes:
  postgres_data:

networks:
  vps-config_default:
    external: true
```

#### 2. Add Reverse Proxy Configuration
Edit `ansible/roles/caddy/templates/Caddyfile.j2`:

```caddy
# Add your custom service
myapp.{{ domain_name }} {
    # Forward authentication through Authelia
    forward_auth authelia:{{ authelia_port }} {
        uri /api/verify?rd=https://auth.{{ domain_name }}/
        copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
    }
    
    # Proxy to your application
    reverse_proxy myapp:8080
    
    # Optional: Add custom headers
    header {
        X-Frame-Options DENY
        X-Content-Type-Options nosniff
    }
    
    # Optional: Enable logging
    log {
        output file /var/log/caddy/myapp.log {
            roll_size 10mb
            roll_keep 5
        }
    }
}

# Public service (no authentication required)
public.{{ domain_name }} {
    reverse_proxy myapp:8080
    
    # Rate limiting for public services
    rate_limit {
        zone myapp {
            key {remote_host}
            events 60
            window 1m
        }
    }
}
```

#### 3. Add DNS Record
Add DNS A record for your new subdomain:
```
Type: A
Name: myapp
Value: YOUR_VPS_IP
TTL: 300
```

#### 4. Deploy
```bash
# Test configuration locally first
just test-local

# Deploy to production
just deploy

# Or deploy only Caddy changes
just update-caddy
```

### Advanced Service Examples

#### Web Application with Database
```yaml
# docker/compose/webapp.yml
version: '3.8'

services:
  webapp:
    image: node:18-alpine
    container_name: webapp
    working_dir: /app
    volumes:
      - ./webapp:/app
    command: npm start
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgres://user:pass@postgres:5432/webapp
    depends_on:
      - postgres
    networks:
      - vps-config_default
    restart: unless-stopped

  postgres:
    image: postgres:15
    container_name: postgres
    environment:
      POSTGRES_DB: webapp
      POSTGRES_USER: webappuser
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    secrets:
      - db_password
    networks:
      - vps-config_default
    restart: unless-stopped

secrets:
  db_password:
    file: ./secrets/db_password.txt

volumes:
  postgres_data:
```

#### Monitoring Integration
Add monitoring for your custom service:

```yaml
# In prometheus.yml.j2, add scrape target
scrape_configs:
  # Your custom application metrics
  - job_name: 'myapp'
    static_configs:
      - targets: ['myapp:9090']  # If your app exposes metrics
    scrape_interval: 30s
    metrics_path: /metrics
```

#### Background Services
```yaml
# docker/compose/workers.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: redis-cache
    command: redis-server --requirepass yourpassword
    volumes:
      - redis_data:/data
    networks:
      - vps-config_default
    restart: unless-stopped

  worker:
    image: python:3.11-alpine
    container_name: background-worker
    volumes:
      - ./worker:/app
    working_dir: /app
    command: python worker.py
    environment:
      - REDIS_URL=redis://:yourpassword@redis-cache:6379/0
    depends_on:
      - redis
    networks:
      - vps-config_default
    restart: unless-stopped

volumes:
  redis_data:
```

## Modifying Existing Services

### Customizing Grafana

#### Add Custom Dashboards
Create dashboard JSON files in `ansible/roles/monitoring/files/dashboards/`:

```json
{
  "dashboard": {
    "id": null,
    "title": "My Application Dashboard",
    "panels": [
      {
        "title": "Application Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

#### Customize Grafana Configuration
Edit `ansible/roles/monitoring/templates/grafana.ini.j2`:

```ini
[server]
domain = grafana.{{ domain_name }}
root_url = https://grafana.{{ domain_name }}

[security]
admin_user = admin
admin_password = {{ grafana_admin_password }}
secret_key = {{ grafana_secret_key }}

[auth.anonymous]
enabled = false

[smtp]
enabled = true
host = {{ smtp_host }}:{{ smtp_port }}
user = {{ smtp_user }}
password = {{ smtp_password }}
from_address = grafana@{{ domain_name }}
```

### Customizing Prometheus

#### Add Custom Alerting Rules
Edit `ansible/roles/monitoring/templates/alert_rules.yml.j2`:

```yaml
groups:
  - name: custom-application-alerts
    rules:
      - alert: ApplicationDown
        expr: up{job="myapp"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "My application is down"
          description: "Application {{ $labels.instance }} has been down for more than 1 minute"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s"
```

#### Custom Prometheus Configuration
Add custom scrape configurations:

```yaml
# In prometheus.yml.j2
scrape_configs:
  # Custom application monitoring
  - job_name: 'custom-apps'
    static_configs:
      - targets: 
        - 'myapp:9090'
        - 'worker:8080'
    scrape_interval: 15s
    metrics_path: /metrics
    basic_auth:
      username: monitoring
      password: secret

  # External service monitoring
  - job_name: 'external-apis'
    static_configs:
      - targets:
        - 'api.example.com'
    scrape_interval: 60s
    metrics_path: /health
    scheme: https
```

### Customizing Authelia

#### Add Custom Access Rules
Edit `ansible/roles/authelia/templates/configuration.yml.j2`:

```yaml
access_control:
  default_policy: deny
  rules:
    # Public endpoints (no auth required)
    - domain: "public.{{ domain_name }}"
      policy: bypass
    
    # API endpoints (different auth requirements)
    - domain: "api.{{ domain_name }}"
      policy: one_factor
      resources:
        - "^/public/.*$"
      
    # Admin area (two-factor + admin group)
    - domain: "admin.{{ domain_name }}"
      policy: two_factor
      subject: "group:admins"
      
    # Development environment (network restricted)
    - domain: "dev.{{ domain_name }}"
      policy: two_factor
      subject: "group:developers"
      networks:
        - "192.168.1.0/24"
        - "10.0.0.0/8"
        
    # Time-based access
    - domain: "restricted.{{ domain_name }}"
      policy: two_factor
      subject: "group:admins"
      methods: ["GET", "POST"]
```

#### Custom User Groups and Permissions
Edit `ansible/roles/authelia/templates/users_database.yml.j2`:

```yaml
users:
  admin:
    displayname: "Administrator"
    password: "{{ authelia_admin_password_hash }}"
    email: "admin@{{ domain_name }}"
    groups:
      - admins
      - developers
      
  developer:
    displayname: "Developer User"
    password: "$argon2id$v=19$..."
    email: "dev@{{ domain_name }}"
    groups:
      - developers
      
  viewer:
    displayname: "Read Only User"
    password: "$argon2id$v=19$..."
    email: "viewer@{{ domain_name }}"
    groups:
      - viewers

groups:
  - name: admins
    description: "Administrators with full access"
  - name: developers  
    description: "Developers with development environment access"
  - name: viewers
    description: "Read-only access to monitoring"
  - name: api-users
    description: "API access only"
```

## Custom Dashboards and Monitoring

### Creating Application Dashboards

#### Metrics Collection
Add metrics endpoint to your application:

```python
# Python Flask example
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('app_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('app_request_duration_seconds', 'Request latency')

@app.route('/metrics')
def metrics():
    return generate_latest()

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    request_latency = time.time() - request.start_time
    REQUEST_LATENCY.observe(request_latency)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.endpoint).inc()
    return response
```

#### Custom Grafana Dashboard
Create dashboard configuration:

```json
{
  "dashboard": {
    "title": "My Application Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(app_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph", 
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(app_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          },
          {
            "expr": "histogram_quantile(0.95, rate(app_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

### Log Analysis Setup

#### Application Logging
Configure structured logging in your application:

```python
import structlog
import json

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_logger_name,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

# Usage in application
logger.info("User login", user_id=123, ip_address="192.168.1.1")
logger.error("Database connection failed", error=str(e), duration=0.5)
```

#### Promtail Configuration
Configure log collection for your application:

```yaml
# In promtail.yml.j2
scrape_configs:
  - job_name: myapp
    static_configs:
      - targets:
          - localhost
        labels:
          job: myapp
          __path__: /opt/logs/myapp/*.log
    pipeline_stages:
      - json:
          expressions:
            timestamp: timestamp
            level: level
            message: message
            user_id: user_id
      - timestamp:
          source: timestamp
          format: RFC3339
      - labels:
          level:
          user_id:
```

## Advanced Configuration

### Multi-Environment Setup

#### Environment-Specific Variables
Create environment-specific configurations:

```bash
# ansible/host_vars/production/main.yml
domain_name: "yourdomain.com"
environment: "production"
log_level: "info"
monitoring_retention: "30d"

# ansible/host_vars/staging/main.yml  
domain_name: "staging.yourdomain.com"
environment: "staging"
log_level: "debug"
monitoring_retention: "7d"
```

#### Conditional Configuration
Use Jinja2 conditionals in templates:

```yaml
# In configuration template
{% if environment == "production" %}
log_level: info
debug_mode: false
{% else %}
log_level: debug
debug_mode: true
{% endif %}

# Resource limits based on environment
{% if environment == "production" %}
memory_limit: 2g
cpu_limit: 2.0
{% else %}
memory_limit: 512m
cpu_limit: 1.0
{% endif %}
```

### Custom SSL Configuration

#### Custom Certificate Authority
For internal services or development:

```yaml
# In Caddyfile template
{
    pki {
        ca internal {
            root_cn "Internal CA"
            intermediate_cn "Internal Intermediate CA" 
        }
    }
}

internal.{{ domain_name }} {
    tls internal  # Use internal CA
    reverse_proxy myapp:8080
}
```

#### Certificate Management
For external certificates:

```caddy
yourdomain.com {
    tls /path/to/cert.pem /path/to/key.pem
    reverse_proxy backend:8080
}
```

### Advanced Networking

#### Custom Docker Networks
Create isolated networks for different service groups:

```yaml
# docker-compose.yml
networks:
  frontend:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
  
  backend:
    driver: bridge  
    ipam:
      config:
        - subnet: 172.21.0.0/16
  
  database:
    driver: bridge
    ipam:
      config:
        - subnet: 172.22.0.0/16

services:
  web:
    networks:
      - frontend
      - backend
      
  api:
    networks:
      - backend
      - database
      
  db:
    networks:
      - database
```

## Development Workflow

### Local Development Setup

#### Development Inventory
Create `ansible/inventories/development.yml`:

```yaml
all:
  hosts:
    dev:
      ansible_connection: local
      ansible_python_interpreter: "{{ ansible_playbook_python }}"
  vars:
    domain_name: "localhost"
    letsencrypt_email: "dev@localhost"
    environment: "development"
```

#### Development-Specific Configuration
```yaml
# In group_vars for development
caddy_image: "caddy:2-alpine"
authelia_image: "authelia/authelia:latest"

# Disable certain features in development
ssl_enabled: false
monitoring_enabled: true
security_hardening: false
```

### Testing Custom Changes

#### Testing Workflow
```bash
# 1. Make changes to configuration
vim ansible/roles/myservice/templates/config.yml.j2

# 2. Test locally
just test-local

# 3. Validate configuration
just validate-full

# 4. Deploy to staging (if available)
just deploy --inventory inventories/staging.yml

# 5. Deploy to production
just deploy
```

#### Custom Validation Scripts
Create validation scripts in `scripts/`:

```python
# scripts/validate_custom.py
import requests
import sys

def validate_custom_service():
    """Validate custom service is responding correctly."""
    try:
        response = requests.get('https://myapp.yourdomain.com/health')
        if response.status_code == 200:
            print("✅ Custom service is healthy")
            return True
        else:
            print(f"❌ Custom service returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Custom service validation failed: {e}")
        return False

if __name__ == "__main__":
    success = validate_custom_service()
    sys.exit(0 if success else 1)
```

## Best Practices

### Configuration Management

#### Version Control
- Keep all configuration in Git
- Use feature branches for major changes
- Tag releases for production deployments
- Document changes in commit messages

```bash
# Example workflow
git checkout -b add-myapp-service
# Make changes
git add -A
git commit -m "Add MyApp service with authentication

- Add Docker service definition
- Configure Caddy reverse proxy  
- Add Prometheus monitoring
- Update documentation"
git push origin add-myapp-service
# Create pull request, review, merge
git tag -a v1.2.0 -m "Release v1.2.0: Add MyApp service"
```

#### Environment Separation
- Use separate inventories for different environments
- Never test directly in production
- Use infrastructure as code principles
- Maintain environment parity where possible

#### Security Considerations
- Never commit secrets to version control
- Use environment variables for sensitive data
- Regularly rotate credentials
- Follow principle of least privilege

#### Monitoring and Observability
- Add health checks for all custom services
- Implement structured logging
- Create custom dashboards for business metrics
- Set up appropriate alerting

#### Documentation
- Document all customizations
- Maintain up-to-date README files
- Include troubleshooting guides
- Document operational procedures

### Service Design Patterns

#### Twelve-Factor App Principles
1. **Codebase**: One codebase tracked in revision control
2. **Dependencies**: Explicitly declare and isolate dependencies
3. **Config**: Store config in the environment
4. **Backing services**: Treat backing services as attached resources
5. **Build, release, run**: Strictly separate build and run stages
6. **Processes**: Execute the app as one or more stateless processes
7. **Port binding**: Export services via port binding
8. **Concurrency**: Scale out via the process model
9. **Disposability**: Maximize robustness with fast startup and graceful shutdown
10. **Dev/prod parity**: Keep development, staging, and production as similar as possible
11. **Logs**: Treat logs as event streams
12. **Admin processes**: Run admin/management tasks as one-off processes

#### Microservices Best Practices
- Design for failure (circuit breakers, retries, timeouts)
- Implement health checks
- Use structured logging and distributed tracing
- Design for scalability and statelessness
- Implement proper service discovery

This customization guide provides the foundation for extending your VPS configuration to meet specific requirements while maintaining security, reliability, and operational excellence.