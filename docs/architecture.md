# Architecture Overview

This document describes the architecture, design decisions, and component relationships of the VPS configuration project.

## System Architecture

The VPS setup follows a containerized, reverse-proxy architecture with centralized authentication and comprehensive monitoring:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Internet (HTTPS Traffic)                   │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                        Caddy Reverse Proxy                          │
│                    (Automatic HTTPS/Let's Encrypt)                  │
└─────────────┬─────────────┬─────────────┬─────────────┬─────────────┘
              │             │             │             │
              ▼             ▼             ▼             ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│    Authelia     │ │   Grafana    │ │  Prometheus  │ │     Loki     │
│  (Port 9091)    │ │ (Port 3000)  │ │ (Port 9090)  │ │ (Port 3100)  │
│                 │ │              │ │              │ │              │
│ Authentication  │ │  Dashboards  │ │   Metrics    │ │     Logs     │
│ & Authorization │ │ & Visualization│ │  Collection  │ │  Aggregation │
└─────────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
          │                                   ▲             ▲
          ▼                                   │             │
┌─────────────────┐                 ┌──────────────┐ ┌──────────────┐
│   Redis Cache   │                 │ Node Exporter│ │   Promtail   │
│ (Port 6379)     │                 │ (Port 9100)  │ │ (Port 9080)  │
│                 │                 │              │ │              │
│ Session Storage │                 │System Metrics│ │Log Collection│
└─────────────────┘                 └──────────────┘ └──────────────┘
```

## Component Architecture

### 1. Reverse Proxy Layer (Caddy)

**Purpose**: Single entry point for all HTTP/HTTPS traffic with automatic SSL management.

**Key Features**:
- Automatic HTTPS with Let's Encrypt certificates
- HTTP to HTTPS redirection
- Forward authentication integration with Authelia
- Load balancing and health checks
- Static file serving capabilities

**Configuration**: `ansible/roles/caddy/templates/Caddyfile.j2`

### 2. Authentication Layer (Authelia)

**Purpose**: Centralized authentication and authorization with 2FA support.

**Architecture**:
```
User Request → Caddy → Authelia (Auth Check) → Protected Service
                 ↓
            Redis Session Store
```

**Key Features**:
- Multi-factor authentication (TOTP)
- Session management with Redis
- User database with groups and permissions
- Rate limiting and regulation
- Forward authentication protocol

**Components**:
- Main service: Authentication engine
- Redis: Session and cache storage
- SQLite: User regulation database

### 3. Monitoring Stack

#### Prometheus (Metrics Collection)
**Purpose**: Time-series metrics collection and alerting.

**Data Sources**:
- Node Exporter: System metrics (CPU, memory, disk, network)
- cAdvisor: Container metrics
- Service endpoints: Application metrics

**Storage**: Local TSDB with 15-day retention

#### Grafana (Visualization)
**Purpose**: Metrics visualization and dashboards.

**Pre-configured Dashboards**:
- System Overview: CPU, memory, disk usage
- Docker Overview: Container metrics
- Logs Overview: Log aggregation and analysis

**Data Sources**:
- Prometheus: Metrics data
- Loki: Log data

#### Loki (Log Aggregation)
**Purpose**: Centralized log collection and querying.

**Architecture**:
```
Container Logs → Promtail → Loki → Grafana
System Logs   ↗
```

**Features**:
- Label-based log indexing
- Efficient storage and compression
- Integration with Grafana for visualization

#### Promtail (Log Collection)
**Purpose**: Log shipping agent for Loki.

**Sources**:
- Docker container logs
- System logs (/var/log)
- Application-specific logs

### 4. Security Layer

#### System Security
- **SSH Hardening**: Key-based authentication, port configuration
- **Firewall**: UFW with restrictive rules
- **Fail2ban**: Intrusion detection and prevention
- **Unattended Upgrades**: Automatic security updates

#### Application Security
- **Container Isolation**: All services run in Docker containers
- **Network Segmentation**: Services communicate through defined networks
- **Secret Management**: Environment-based secret injection
- **HTTPS Enforcement**: All traffic encrypted with valid certificates

## Data Flow Patterns

### 1. Authentication Flow
```
1. User → https://service.domain.com
2. Caddy → Check with Authelia
3. If not authenticated → Redirect to auth.domain.com
4. User authenticates (username/password + 2FA)
5. Authelia creates session → Stores in Redis
6. User redirected back to original service
7. Subsequent requests use session cookie
```

### 2. Monitoring Data Flow
```
1. Node Exporter → Exposes system metrics
2. Prometheus → Scrapes metrics every 15s
3. Grafana → Queries Prometheus for dashboards
4. Promtail → Collects logs from containers/system
5. Loki → Stores and indexes logs
6. Grafana → Queries Loki for log visualization
```

### 3. Request Processing Flow
```
Internet → Caddy (HTTPS termination) → Authelia (Auth) → Service Container
    ↓
Let's Encrypt (Certificate Management)
    ↓
Prometheus (Metrics Collection)
    ↓
Loki (Log Aggregation)
```

## Directory Structure and Organization

### Ansible Organization
```
ansible/
├── playbooks/
│   └── site.yml              # Main orchestration playbook
├── roles/                    # Service-specific configurations
│   ├── common/              # Base system setup
│   ├── security/            # Security hardening
│   ├── docker/              # Container runtime
│   ├── authelia/            # Authentication service
│   ├── caddy/               # Reverse proxy
│   └── monitoring/          # Observability stack
├── inventories/             # Environment configurations
│   ├── hosts.yml           # Template inventory
│   ├── production.yml      # Production environment
│   └── production/         # Environment-specific secrets
└── group_vars/
    └── all.yml             # Global variables
```

### Service Data Persistence
```
/opt/                        # Base directory for all services
├── authelia/               # Authentication data
│   ├── config/            # Configuration files
│   └── data/              # User database, sessions
├── caddy/                 # Reverse proxy data
│   ├── config/            # Caddyfile and SSL configs
│   └── data/              # SSL certificates, cache
├── prometheus/            # Metrics storage
│   └── data/              # Time-series database
├── grafana/               # Dashboard data
│   ├── data/              # Dashboard configs, users
│   └── provisioning/      # Automated provisioning
├── loki/                  # Log storage
│   └── data/              # Log index and chunks
└── logs/                  # Centralized log collection
```

## Network Architecture

### Docker Networks
- **monitoring**: Internal network for metrics collection
- **auth**: Network for authentication services
- **web**: Network for web-facing services
- **bridge**: Default Docker bridge for inter-container communication

### Port Configuration
```
External (Internet):
├── 80/tcp   → Caddy (HTTP redirect to HTTPS)
├── 443/tcp  → Caddy (HTTPS)
└── 22/tcp   → SSH (configurable)

Internal (Docker):
├── 9091/tcp → Authelia
├── 3000/tcp → Grafana  
├── 9090/tcp → Prometheus
├── 3100/tcp → Loki
├── 9100/tcp → Node Exporter
├── 6379/tcp → Redis
└── 9080/tcp → Promtail
```

## Scalability Considerations

### Horizontal Scaling
- **Load Balancing**: Caddy supports upstream load balancing
- **Service Replication**: Docker services can be scaled using replicas
- **Database Scaling**: Redis supports clustering for session storage

### Vertical Scaling
- **Resource Allocation**: Docker containers have configurable resource limits
- **Storage**: Volumes can be resized for data persistence
- **Monitoring**: Prometheus and Loki can handle increased load with configuration tuning

### High Availability
- **Health Checks**: All services include health check endpoints
- **Automatic Restart**: Docker restart policies ensure service recovery
- **Backup Strategy**: Critical data is backed up regularly
- **Certificate Renewal**: Automatic Let's Encrypt certificate renewal

## Security Architecture

### Defense in Depth
1. **Network Level**: Firewall rules, fail2ban
2. **Transport Level**: HTTPS encryption, certificate validation
3. **Authentication Level**: 2FA, session management
4. **Authorization Level**: Role-based access control
5. **Application Level**: Container isolation, secret management

### Secret Management
- Environment variables for runtime secrets
- File-based secrets with restricted permissions (0600)
- Separation of configuration and secrets
- No secrets in version control

### Monitoring and Alerting
- Security event logging
- Failed authentication tracking  
- System resource monitoring
- Service health monitoring

## Technology Choices and Rationale

### Why Caddy?
- **Automatic HTTPS**: Zero-configuration SSL certificates
- **Simplicity**: Easy configuration syntax
- **Performance**: Efficient reverse proxy with HTTP/2 support
- **Extensibility**: Plugin ecosystem for additional features

### Why Authelia?
- **Comprehensive**: Full-featured authentication with 2FA
- **Integration**: Works seamlessly with reverse proxies
- **Security**: Modern authentication standards
- **Open Source**: Active development and community support

### Why Prometheus Stack?
- **Industry Standard**: De facto standard for metrics monitoring
- **Scalability**: Handles large volumes of metrics efficiently
- **Ecosystem**: Large ecosystem of exporters and tools
- **Query Language**: Powerful PromQL for metrics analysis

### Why Docker?
- **Isolation**: Service isolation and security
- **Portability**: Consistent environments across development and production
- **Resource Efficiency**: Better resource utilization than VMs
- **Orchestration**: Easy service management and scaling