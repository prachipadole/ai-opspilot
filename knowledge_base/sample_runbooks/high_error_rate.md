# Runbook: High HTTP Error Rate (5xx)

## Symptoms
- HTTP 500/502/503/504 error rate > 5% (measured over 5-minute window)
- Upstream service timeouts in Nginx/proxy logs
- Increased Sentry/error-tracker alerts

## Root Cause Categories
1. **Application crash** / unhandled exception
2. **Upstream dependency down** (DB, cache, external API)
3. **Deployment failure** – new bad version rolled out
4. **Resource exhaustion** (CPU/memory/disk)

## Diagnosis Steps

```bash
# Check recent 5xx errors in Nginx
grep ' 5[0-9][0-9] ' /var/log/nginx/access.log | tail -50

# Check application error logs
journalctl -u myapp --since "5 minutes ago" | grep -i error

# Kubernetes pod status
kubectl get pods -n <namespace>
kubectl describe pod <failing-pod> -n <namespace>
kubectl logs <failing-pod> -n <namespace> --tail=100
```

## Remediation

### Option A – Rollback deployment
```bash
kubectl rollout undo deployment/<deployment> -n <namespace>
kubectl rollout status deployment/<deployment> -n <namespace>
```

### Option B – Restart pods
```bash
kubectl delete pods -l app=<app-label> -n <namespace>
```

### Option C – Scale up to absorb load
```bash
kubectl scale deployment/<deployment> --replicas=<n> -n <namespace>
```

## Prevention
- Blue-green or canary deployments
- Readiness / liveness probes on all pods
- Alert on `http_requests_total{status=~"5.."} / http_requests_total > 0.05`
