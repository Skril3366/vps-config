# Development Guide

This guide covers local development, testing, and contribution workflows for the VPS configuration project.

## Table of Contents
- [Development Environment Setup](#development-environment-setup)
- [Local Testing Workflow](#local-testing-workflow)
- [Code Structure and Standards](#code-structure-and-standards)
- [Testing and Validation](#testing-and-validation)
- [Contributing Guidelines](#contributing-guidelines)
- [Debugging and Troubleshooting](#debugging-and-troubleshooting)

## Development Environment Setup

### Prerequisites

#### Required Tools
```bash
# macOS
brew install just uv docker git ansible

# Ubuntu/Debian
sudo apt update
sudo apt install -y git python3 python3-pip docker.io
curl -LsSf https://astral.sh/uv/install.sh | sh
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/bin
pip3 install ansible
```

#### Development Dependencies
```bash
# Install project dependencies
uv sync

# Install additional development tools
uv add --dev pytest ansible-lint yamllint black isort mypy
```

### Project Structure

```
vps-config/
├── ansible/                    # Ansible automation
│   ├── ansible.cfg            # Ansible configuration
│   ├── group_vars/            # Global variables
│   ├── host_vars/             # Host-specific variables
│   ├── inventories/           # Environment configurations
│   ├── playbooks/             # Orchestration playbooks
│   └── roles/                 # Service-specific roles
│       ├── common/            # Base system setup
│       ├── security/          # Security hardening
│       ├── docker/            # Container runtime
│       ├── authelia/          # Authentication
│       ├── caddy/             # Reverse proxy
│       └── monitoring/        # Observability stack
├── docker/                    # Docker configurations
│   ├── compose/               # Service definitions
│   └── test-environment/      # Local testing setup
├── scripts/                   # Python automation tools
│   ├── validate.py            # Configuration validation
│   ├── test_local.py          # Local testing
│   └── utilities/             # Helper utilities
├── docs/                      # Documentation
├── justfile                   # Task automation
└── pyproject.toml             # Project configuration
```

### Local Configuration

#### Development Inventory
Create `ansible/inventories/development.yml`:

```yaml
---
all:
  hosts:
    local:
      ansible_connection: local
      ansible_python_interpreter: "{{ ansible_playbook_python }}"
      ansible_become: no
  
  vars:
    domain_name: "localhost"
    letsencrypt_email: "dev@localhost"
    environment: "development"
    
    # Development-specific overrides
    ssl_enabled: false
    fail2ban_enabled: false
    unattended_upgrades_enabled: false
    
    # Use latest images for development
    caddy_image: "caddy:2-alpine"
    authelia_image: "authelia/authelia:latest"
```

#### Environment Variables
Create `.env.development`:

```bash
# Development environment variables
AUTHELIA_JWT_SECRET="development-jwt-secret-not-for-production"
AUTHELIA_SESSION_SECRET="development-session-secret"
AUTHELIA_STORAGE_ENCRYPTION_KEY="development-storage-key"

AUTHELIA_ADMIN_USER=admin
AUTHELIA_ADMIN_DISPLAYNAME=Admin
AUTHELIA_ADMIN_EMAIL=admin@localhost
AUTHELIA_ADMIN_PASSWORD_HASH=$argon2id$v=19$m=65536,t=3,p=4$development$hash

# Development flags
DEBUG=true
LOG_LEVEL=debug
```

## Local Testing Workflow

### Testing Infrastructure

The project includes a Docker-based testing environment that simulates the target VPS:

#### Test Environment Components
- **Base Container**: Ubuntu with systemd support
- **Ansible Target**: Configured as deployment target  
- **Service Simulation**: All services run as containers
- **Network Isolation**: Isolated Docker network
- **Volume Persistence**: Temporary volumes for testing

#### Running Local Tests

```bash
# Full local test cycle
just test-local

# What this does:
# 1. Builds test Docker environment
# 2. Applies full Ansible configuration
# 3. Starts all services
# 4. Runs health checks
# 5. Reports results
```

#### Accessing Test Services
During testing, services are available on different ports:

```bash
# SSH to test container
ssh -p 2222 root@localhost

# Service access URLs
echo "Caddy HTTP: http://localhost:8080"
echo "Grafana: http://localhost:3001"
echo "Prometheus: http://localhost:9091"
echo "Authelia: http://localhost:9092"

# Direct container access
docker exec -it test-container /bin/bash
```

#### Test Environment Management
```bash
# Start test environment
just test-local

# Clean up test environment
just test-clean

# Rebuild test environment from scratch
just test-clean && just test-local

# View test container logs
docker logs test-container

# Monitor test container
docker exec test-container systemctl status
```

### Development Workflow

#### 1. Make Changes
```bash
# Edit configuration files
vim ansible/roles/caddy/templates/Caddyfile.j2
vim ansible/group_vars/all.yml

# Edit scripts
vim scripts/validate.py
```

#### 2. Validate Changes
```bash
# Run syntax validation
just check

# Run comprehensive validation
just validate-full

# Check for linting issues
ansible-lint ansible/
yamllint ansible/
```

#### 3. Test Locally
```bash
# Test changes in local environment
just test-local

# Check specific service logs
docker exec test-container journalctl -u docker
docker logs test-caddy
```

#### 4. Incremental Testing
For faster iteration during development:

```bash
# Test specific role only
ansible-playbook ansible/playbooks/site.yml -i ansible/inventories/development.yml --tags caddy

# Test specific tasks
ansible-playbook ansible/playbooks/site.yml -i ansible/inventories/development.yml --start-at-task="Deploy Caddy"
```

### Custom Test Scenarios

#### Testing Configuration Changes
```bash
# Test specific configuration change
echo "Testing new Caddy configuration..."
just test-local

# Verify configuration
docker exec test-container cat /opt/caddy/Caddyfile

# Test service restart
docker exec test-container docker restart caddy
```

#### Testing Security Changes
```bash
# Test firewall rules
docker exec test-container ufw status

# Test SSH configuration
docker exec test-container sshd -T

# Test fail2ban
docker exec test-container fail2ban-client status
```

## Code Structure and Standards

### Ansible Best Practices

#### Directory Structure
```
roles/service-name/
├── defaults/
│   └── main.yml          # Default variables
├── files/
│   └── static-file       # Static files to copy
├── handlers/
│   └── main.yml          # Event handlers (restart, reload)
├── meta/
│   └── main.yml          # Role metadata and dependencies
├── tasks/
│   └── main.yml          # Main task definitions
├── templates/
│   └── config.j2         # Jinja2 templates
└── vars/
    └── main.yml          # Role-specific variables
```

#### Task Writing Standards
```yaml
---
# Good task example
- name: Install essential packages
  apt:
    name: "{{ essential_packages }}"
    state: present
    update_cache: yes
    cache_valid_time: "{{ apt_cache_valid_time }}"
  become: yes
  tags:
    - packages
    - common

- name: Create service directory
  file:
    path: "{{ service_directory }}"
    state: directory
    owner: root
    group: root
    mode: '0755'
  become: yes
  tags:
    - directories

- name: Deploy service configuration
  template:
    src: service.conf.j2
    dest: "{{ service_directory }}/service.conf"
    owner: root
    group: root
    mode: '0644'
    backup: yes
  become: yes
  notify:
    - restart service
  tags:
    - configuration
```

#### Variable Naming Conventions
```yaml
# Use descriptive, hierarchical names
service_name: "myservice"
service_version: "1.0.0"  
service_port: 8080
service_directory: "/opt/{{ service_name }}"
service_config_directory: "{{ service_directory }}/config"
service_data_directory: "{{ service_directory }}/data"

# Boolean variables
service_enabled: true
service_ssl_enabled: false
service_monitoring_enabled: true

# Lists and dictionaries
service_dependencies:
  - package1
  - package2

service_configuration:
  log_level: info
  max_connections: 100
```

#### Template Best Practices
```jinja2
{# Jinja2 template example #}
# {{ ansible_managed }}
# Configuration for {{ service_name }}

[server]
host = {{ service_host | default('0.0.0.0') }}
port = {{ service_port }}

{% if service_ssl_enabled %}
[ssl]
cert_file = {{ ssl_cert_path }}
key_file = {{ ssl_key_path }}
{% endif %}

{% for item in service_items %}
item_{{ loop.index }} = {{ item }}
{% endfor %}

# Environment-specific settings
{% if environment == 'development' %}
debug = true
log_level = debug
{% else %}
debug = false
log_level = {{ log_level | default('info') }}
{% endif %}
```

### Python Code Standards

#### Code Style
```python
# Use Black for formatting
# Use isort for import sorting
# Follow PEP 8 guidelines

import os
import sys
from typing import Dict, List, Optional

import requests
import yaml


class ConfigValidator:
    """Validates VPS configuration files and settings."""
    
    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.errors: List[str] = []
    
    def validate_config(self) -> bool:
        """Validate configuration files.
        
        Returns:
            bool: True if validation passes, False otherwise.
        """
        try:
            return self._check_syntax() and self._check_requirements()
        except Exception as e:
            self.errors.append(f"Validation error: {e}")
            return False
    
    def _check_syntax(self) -> bool:
        """Check YAML syntax."""
        # Implementation here
        return True
```

#### Error Handling
```python
def deploy_service(service_name: str) -> bool:
    """Deploy a service with proper error handling."""
    try:
        logger.info(f"Deploying service: {service_name}")
        
        # Validate before deployment
        if not validate_service_config(service_name):
            raise ValueError(f"Invalid configuration for {service_name}")
        
        # Deploy service
        result = run_ansible_playbook(service_name)
        
        if result.returncode != 0:
            logger.error(f"Deployment failed: {result.stderr}")
            return False
            
        logger.info(f"Successfully deployed {service_name}")
        return True
        
    except Exception as e:
        logger.error(f"Deployment error for {service_name}: {e}")
        return False
    finally:
        cleanup_temp_files()
```

#### Configuration Classes
```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class ServiceConfig:
    """Configuration for a service deployment."""
    name: str
    version: str
    port: int
    enabled: bool = True
    ssl_enabled: bool = False
    monitoring_enabled: bool = True
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port number: {self.port}")
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ServiceConfig':
        """Create ServiceConfig from dictionary."""
        return cls(**data)
```

### Documentation Standards

#### README Format
Each role should include a README.md:

```markdown
# Role Name

Brief description of what this role does.

## Requirements

- Ubuntu 20.04+
- Docker installed
- Sudo access

## Role Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `service_port` | `8080` | Port for service to listen on |
| `service_enabled` | `true` | Whether to enable the service |

## Dependencies

- common
- docker

## Example Playbook

```yaml
- hosts: servers
  roles:
    - { role: service-name, service_port: 9090 }
```

## Testing

Run tests with:
```bash
molecule test
```
```

#### Code Comments
```yaml
---
# Main tasks for service deployment
# This role configures and deploys the service with monitoring

- name: Create service user
  user:
    name: "{{ service_user }}"
    system: yes
    shell: /bin/false
    home: "{{ service_directory }}"
    createhome: no
  become: yes
  # Service user is created as system account for security

- name: Deploy service configuration
  template:
    src: service.conf.j2
    dest: "{{ service_config_path }}"
    owner: "{{ service_user }}"
    group: "{{ service_group }}"
    mode: '0644'
  become: yes
  notify: restart service
  # Configuration template includes environment-specific settings
```

## Testing and Validation

### Automated Testing

#### Validation Scripts
```python
# scripts/test_deployment.py
import subprocess
import sys
from typing import List


def run_tests() -> bool:
    """Run all deployment tests."""
    test_functions = [
        test_ansible_syntax,
        test_docker_services,
        test_ssl_certificates,
        test_authentication_flow,
    ]
    
    results = []
    for test_func in test_functions:
        try:
            result = test_func()
            results.append(result)
            print(f"✅ {test_func.__name__}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            print(f"❌ {test_func.__name__}: ERROR - {e}")
            results.append(False)
    
    return all(results)


def test_ansible_syntax() -> bool:
    """Test Ansible playbook syntax."""
    result = subprocess.run(
        ["ansible-playbook", "--syntax-check", "ansible/playbooks/site.yml"],
        capture_output=True,
        text=True
    )
    return result.returncode == 0
```

#### Integration Tests
```bash
#!/bin/bash
# scripts/integration_test.sh

set -e

echo "🧪 Starting integration tests..."

# Test service deployment
echo "Testing service deployment..."
just test-local

# Test service health
echo "Testing service health..."
curl -f http://localhost:8080/health || exit 1
curl -f http://localhost:3001/api/health || exit 1

# Test authentication flow
echo "Testing authentication..."
python scripts/test_auth_flow.py || exit 1

# Test monitoring
echo "Testing monitoring..."
curl -f http://localhost:9091/api/v1/targets || exit 1

echo "✅ All integration tests passed!"
```

### Manual Testing Procedures

#### Pre-Deployment Testing
```bash
# 1. Validate configuration
just validate-full

# 2. Test locally
just test-local

# 3. Check for security issues
ansible-lint ansible/
bandit -r scripts/

# 4. Check documentation
markdown-lint docs/
```

#### Post-Deployment Testing
```bash
# 1. Health checks
just health-check

# 2. Service functionality
curl -I https://auth.yourdomain.com
curl -I https://grafana.yourdomain.com

# 3. Authentication flow
# Manual login test through web interface

# 4. Monitoring data
# Check Grafana dashboards show data
# Check Prometheus targets are up
```

### Performance Testing

#### Load Testing
```python
# scripts/load_test.py
import asyncio
import aiohttp
import time
from typing import List


async def load_test_endpoint(url: str, concurrent_requests: int = 10, duration: int = 60):
    """Load test an endpoint."""
    start_time = time.time()
    request_count = 0
    error_count = 0
    
    async with aiohttp.ClientSession() as session:
        while time.time() - start_time < duration:
            tasks = []
            for _ in range(concurrent_requests):
                task = make_request(session, url)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                else:
                    request_count += 1
    
    total_time = time.time() - start_time
    print(f"Requests: {request_count}, Errors: {error_count}")
    print(f"RPS: {request_count / total_time:.2f}")
    print(f"Error Rate: {error_count / (request_count + error_count) * 100:.2f}%")


async def make_request(session, url):
    """Make a single HTTP request."""
    async with session.get(url) as response:
        return await response.text()
```

## Contributing Guidelines

### Development Process

#### 1. Fork and Clone
```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/yourusername/vps-config.git
cd vps-config

# Add upstream remote
git remote add upstream https://github.com/original/vps-config.git
```

#### 2. Create Feature Branch
```bash
# Create and switch to feature branch
git checkout -b feature/add-new-service

# Work on your changes
vim ansible/roles/newservice/tasks/main.yml
```

#### 3. Test Changes
```bash
# Test locally
just test-local

# Run validation
just validate-full

# Test on staging environment (if available)
just deploy --inventory inventories/staging.yml
```

#### 4. Commit and Push
```bash
# Stage changes
git add -A

# Commit with descriptive message
git commit -m "Add new service configuration

- Add Docker service definition
- Configure reverse proxy integration
- Add monitoring and health checks
- Update documentation

Closes #123"

# Push to your fork
git push origin feature/add-new-service
```

#### 5. Create Pull Request
- Open pull request on GitHub
- Provide detailed description
- Include testing evidence
- Reference related issues

### Code Review Checklist

#### For Reviewers
- [ ] Changes follow project conventions
- [ ] Code is well-documented
- [ ] Tests pass locally
- [ ] Security implications considered
- [ ] Performance impact assessed
- [ ] Documentation updated
- [ ] Backward compatibility maintained

#### For Contributors
- [ ] Local testing completed
- [ ] Validation scripts pass
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No sensitive data in commits
- [ ] Changes are focused and atomic

## Debugging and Troubleshooting

### Common Development Issues

#### Ansible Issues
```bash
# Debug Ansible execution
ansible-playbook -vvv ansible/playbooks/site.yml -i inventories/development.yml

# Check Ansible facts
ansible -m setup localhost

# Test specific module
ansible -m ping all -i inventories/development.yml
```

#### Docker Issues
```bash
# Debug container issues
docker logs <container-name>
docker exec -it <container-name> /bin/bash

# Check container resource usage
docker stats

# Inspect container configuration
docker inspect <container-name>
```

#### Service Configuration Issues
```bash
# Check service configuration
docker exec <container> cat /etc/service/config.yml

# Test service configuration
docker exec <container> service-name --test-config

# Check service logs
docker logs <container> | grep ERROR
```

### Debugging Tools and Techniques

#### Local Development Debugging
```bash
# Enable debug logging
export DEBUG=true
export ANSIBLE_DEBUG=true

# Use Python debugger
import pdb; pdb.set_trace()

# Verbose output
ansible-playbook -vvv ...
docker-compose up --verbose
```

#### Production Debugging
```bash
# Remote debugging (be careful!)
just ssh "systemctl status docker"
just ssh "docker ps -a"
just logs <service> | tail -50

# Check system resources
just ssh "free -h && df -h && uptime"
```

This development guide provides comprehensive information for contributing to and maintaining the VPS configuration project. Following these guidelines ensures consistent, reliable, and secure deployments.