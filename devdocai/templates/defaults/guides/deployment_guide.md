---
metadata:
  id: deployment_guide_standard
  name: Deployment Guide Template
  description: Step-by-step deployment guide
  category: guides
  type: deployment_guide
  version: 1.0.0
  author: DevDocAI
  tags: [deployment, production, devops]
variables:
  - name: project_name
    required: true
    type: string
  - name: platform
    required: false
    type: string
    default: "AWS"
---

# {{project_name}} Deployment Guide

This guide covers deploying {{project_name}} to {{platform}}.

## Prerequisites

- {{platform}} account
- Docker installed
- kubectl configured (for Kubernetes)

## Deployment Steps

### 1. Prepare Application

```bash
# Build the application
npm run build

# Create Docker image
docker build -t {{project_name}}:latest .

# Tag for registry
docker tag {{project_name}}:latest registry/{{project_name}}:latest
```

### 2. Deploy to {{platform}}

```bash
# Push to registry
docker push registry/{{project_name}}:latest

# Apply Kubernetes manifests
kubectl apply -f k8s/

# Verify deployment
kubectl get pods
```

### 3. Configure Environment

- Set environment variables
- Configure database connections
- Set up monitoring
- Configure SSL certificates

### 4. Verify Deployment

- Test application endpoints
- Check logs
- Monitor metrics
- Run health checks

## Rollback Procedure

If deployment fails:

1. Identify the issue
2. Rollback to previous version
3. Investigate and fix
4. Redeploy

## Monitoring

- Application logs: `/var/log/{{project_name}}`
- Metrics: Available at `/metrics` endpoint
- Health check: `/health` endpoint
