# Project Deployment Guide

This guide explains how to deploy your own applications and services to the VPS using a unified Docker-based approach.

## Architecture Overview

The VPS supports deploying custom projects through:
- **Docker containers** for isolation and consistency
- **Caddy reverse proxy** for routing and HTTPS
- **Path-based routing** under `projects.yourdomain.com`
- **Unified deployment workflow** for all project types

### Supported Project Types

| Type | Description | Example |
|------|-------------|---------|
| **Static Sites** | HTML/JS/CSS files served by nginx | Portfolio, game builds, documentation |
| **Single Page Apps** | React/Vue/Angular frontends | Web applications |
| **API Backends** | REST/GraphQL APIs | Node.js, Python, Go services |
| **Full-Stack Apps** | Combined frontend + backend | Complete web applications |

## Quick Start: Adding a New Project

### Step 1: Configure in VPS Repository

Add your project to `ansible/group_vars/all.yml`:

```yaml
# Add to existing projects list (or create if doesn't exist)
projects:
  - name: infinite-echoes
    type: static
    port: 8001
    image: "your-registry/infinite-echoes:latest"
    auth_required: false
    subdomain: "projects"  # Will serve at projects.domain.com/infinite-echoes
    
  - name: my-api
    type: backend
    port: 8002
    image: "your-registry/my-api:latest"
    auth_required: true
    subdomain: "api"       # Will serve at api.domain.com
```

### Step 2: Update Caddy Configuration

The projects role will automatically generate Caddy rules, but you can customize in `ansible/roles/caddy/templates/Caddyfile.j2`.

### Step 3: Deploy VPS Configuration

```bash
# Test configuration locally first
just test-local

# Check syntax
just check

# Dry run to see changes
just dry-run

# Deploy to production
just deploy
```

### Step 4: Configure Project Repository

#### For Static Sites (like infinite-echoes):

Add to your project's GitHub Actions:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Your build steps here
      - name: Build and pack
        run: just pack  # or your build command

      # Build Docker image
      - name: Build Docker image
        run: |
          cat > Dockerfile << EOF
          FROM nginx:alpine
          COPY deploy/ /usr/share/nginx/html/
          EXPOSE 80
          EOF
          docker build -t infinite-echoes:latest .

      # Push to registry (optional - or use direct deployment)
      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker push your-registry/infinite-echoes:latest

      # Deploy to VPS
      - name: Deploy to VPS
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H ${{ secrets.DEPLOY_SERVER_IP }} >> ~/.ssh/known_hosts
          
          # Pull new image and restart container
          ssh deployer@${{ secrets.DEPLOY_SERVER_IP }} "
            docker pull your-registry/infinite-echoes:latest
            docker stop infinite-echoes || true
            docker rm infinite-echoes || true
            docker run -d --name infinite-echoes --restart unless-stopped -p 8001:80 your-registry/infinite-echoes:latest
          "
```

#### For Backend Services:

```yaml
# Similar workflow but with your API Dockerfile
FROM node:alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
```

## Detailed Implementation Steps

### 1. Create Projects Role

The infrastructure needs a new `ansible/roles/projects/` role:

```
ansible/roles/projects/
├── tasks/main.yml          # Deploy project containers
├── templates/
│   └── project-caddy.j2    # Caddy config fragment
├── handlers/main.yml       # Restart handlers
└── defaults/main.yml       # Default variables
```

### 2. Project Configuration Schema

```yaml
# In group_vars/all.yml
projects:
  - name: string              # Container name and path segment
    type: static|backend|spa  # Project type
    port: number              # Internal container port
    image: string             # Docker image to deploy
    auth_required: boolean    # Whether to require Authelia auth
    subdomain: string         # Subdomain to serve under
    environment:              # Optional environment variables
      - KEY=value
    volumes:                  # Optional volume mounts
      - host_path:container_path
```

### 3. Deployment Workflow Options

#### Option A: Registry-Based Deployment
Build and push to Docker registry, then pull on VPS:

```yaml
- name: Build and push Docker image
  run: |
    cat > Dockerfile << EOF
    FROM nginx:alpine
    COPY deploy/ /usr/share/nginx/html/
    EXPOSE 80
    EOF
    docker build -t your-registry/infinite-echoes:latest .
    
    echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
    docker push your-registry/infinite-echoes:latest

- name: Deploy to VPS
  run: |
    mkdir -p ~/.ssh
    echo "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/id_rsa
    chmod 600 ~/.ssh/id_rsa
    ssh-keyscan -H ${{ secrets.DEPLOY_SERVER_IP }} >> ~/.ssh/known_hosts
    
    ssh deployer@${{ secrets.DEPLOY_SERVER_IP }} "
      docker pull your-registry/infinite-echoes:latest
      docker stop infinite-echoes || true
      docker rm infinite-echoes || true
      docker run -d --name infinite-echoes --restart unless-stopped -p 8001:80 your-registry/infinite-echoes:latest
    "
```

#### Option B: Build & Transfer Image
Build Docker image in CI and transfer directly to VPS without registry:

```yaml
- name: Build Docker image
  run: |
    cat > Dockerfile << EOF
    FROM nginx:alpine
    COPY deploy/ /usr/share/nginx/html/
    EXPOSE 80
    EOF
    docker build -t infinite-echoes:latest .

- name: Save and transfer image
  run: |
    # Save image to compressed tar
    docker save infinite-echoes:latest | gzip > infinite-echoes.tar.gz
    
    # Setup SSH
    mkdir -p ~/.ssh
    echo "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/id_rsa
    chmod 600 ~/.ssh/id_rsa
    ssh-keyscan -H ${{ secrets.DEPLOY_SERVER_IP }} >> ~/.ssh/known_hosts
    
    # Transfer to VPS
    scp infinite-echoes.tar.gz deployer@${{ secrets.DEPLOY_SERVER_IP }}:/tmp/
    
    # Load and deploy on VPS
    ssh deployer@${{ secrets.DEPLOY_SERVER_IP }} "
      docker load < /tmp/infinite-echoes.tar.gz
      docker stop infinite-echoes || true
      docker rm infinite-echoes || true
      docker run -d --name infinite-echoes --restart unless-stopped -p 8001:80 infinite-echoes:latest
      rm /tmp/infinite-echoes.tar.gz
    "
```

## Advanced Features

### Authentication Integration

Projects can be protected with Authelia:

```yaml
- name: admin-panel
  type: spa
  port: 8003
  image: "your-registry/admin:latest"
  auth_required: true  # Will require login via auth.domain.com
```

### Environment Variables

Pass runtime configuration:

```yaml
- name: api-service
  type: backend
  port: 8004
  image: "your-registry/api:latest"
  environment:
    - DATABASE_URL=postgres://...
    - API_KEY_SECRET=xxx
```

### Custom Domains

Use dedicated subdomains for major projects:

```yaml
- name: main-app
  type: spa
  port: 8005
  image: "your-registry/app:latest"
  subdomain: "app"  # Serves at app.domain.com instead of projects.domain.com/app
```

## Monitoring Integration

Projects automatically get:
- **Container metrics** via cAdvisor
- **HTTP metrics** via Caddy/Prometheus
- **Log collection** via Promtail/Loki
- **Grafana dashboards** for project monitoring

## Security Considerations

- All traffic encrypted with automatic HTTPS
- Container isolation prevents cross-project interference  
- Optional Authelia authentication for sensitive services
- Fail2ban protection against brute force attacks
- Regular security updates via unattended-upgrades

## Subpath Configuration

### Understanding Subpath Issues

When serving applications under subpaths (like `projects.domain.com/infinite-echoes`), you may encounter asset loading issues if your application uses absolute paths in HTML/JavaScript.

#### Common Problem
Your HTML contains absolute paths:
```html
<link rel="stylesheet" href="/style.css">
<script src="/game.js"></script>
```

When served under `/infinite-echoes/`, the browser requests:
- `/style.css` ❌ (404 - file not found at root)
- Instead of `/infinite-echoes/style.css` ✅

#### Solution: Asset Path Handling

The Caddy configuration automatically handles this by:

1. **Main app routing**: Strips prefix for HTML pages
   ```
   /infinite-echoes/ → / (nginx receives correct path)
   ```

2. **Asset routing**: Catches absolute asset requests with referer detection
   ```
   /game_bg.wasm + Referer: infinite-echoes → forwards to nginx
   ```

#### Caddy Configuration Pattern
```caddy
# Handle main app page
handle /{{ project.name }}/* {
    uri strip_prefix /{{ project.name }}
    reverse_proxy 127.0.0.1:{{ project.port }}
}
handle /{{ project.name }} {
    redir /{{ project.name }}/ permanent
}

# Handle any absolute paths from this project (based on referer)
@{{ project.name }}_assets {
    header Referer *{{ project.name }}*
    not path /{{ project.name }}/*
}
handle @{{ project.name }}_assets {
    reverse_proxy 127.0.0.1:{{ project.port }}
}
```

### Best Practices

#### For Static Sites with Absolute Paths
- Use the current configuration (works automatically)
- No changes needed in your application code
- Assets are served correctly via referer-based routing

#### For New Applications
Consider building with relative paths for better portability:
```html
<link rel="stylesheet" href="./style.css">
<script src="./game.js"></script>
```

#### For Complex SPAs
Consider using dedicated subdomains instead:
```yaml
projects:
  - name: complex-app
    subdomain: "app"  # Serves at app.domain.com instead of projects.domain.com/app
```

### Asset Handling Strategy

The configuration uses **referer-based routing** to automatically handle any absolute path request that comes from your project pages:

- **Automatic**: Works with any file type or path structure
- **Smart detection**: Uses HTTP referer header to identify requests from your app
- **No configuration needed**: Handles unknown asset types without manual setup

This means your project can use absolute paths (`/any-file.extension`) and they'll be routed correctly without requiring specific file type configuration.

## Troubleshooting

### Check Project Status
```bash
# View running containers
just ssh
docker ps

# Check specific project logs
just logs infinite-echoes

# Restart project
just restart infinite-echoes
```

### Update Project
```bash
# Pull latest image and restart
ssh deployer@your-vps "docker pull your-registry/project:latest && docker restart project-name"

# Or trigger full redeployment
just deploy
```

### Check Caddy Routing
```bash
# Test routing
curl -I https://projects.yourdomain.com/infinite-echoes

# View Caddy logs
just logs caddy
```