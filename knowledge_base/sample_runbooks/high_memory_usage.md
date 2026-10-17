# Runbook: High Memory Usage

## Symptoms
- Memory utilisation > 90% on one or more application nodes
- OOMKiller events in kernel logs (`dmesg | grep -i oom`)
- Degraded response times, service restarts

## Root Cause Categories
1. **Memory leak** in application code (most common)
2. **Insufficient heap allocation** for current load
3. **Misconfigured JVM/runtime** settings
4. **Runaway query** holding large result sets in memory

## Diagnosis Steps

```bash
# 1. Check overall memory
free -h
vmstat -s | head -10

# 2. Find top memory-consuming processes
ps aux --sort=-%mem | head -20

# 3. Inspect container stats (if containerised)
docker stats --no-stream

# 4. Kubernetes memory per pod
kubectl top pods -n <namespace> --sort-by=memory
```

## Remediation

### Option A – Immediate (Restart leaking service)
```bash
# Docker
docker restart <container_name>

# Kubernetes
kubectl rollout restart deployment/<deployment> -n <namespace>
```

### Option B – Scale out (if load-driven)
```bash
kubectl scale deployment/<deployment> --replicas=<n> -n <namespace>
```

### Option C – Increase memory limits (Kubernetes)
```yaml
resources:
  requests:
    memory: "512Mi"
  limits:
    memory: "2Gi"
```

## Prevention
- Set JVM `-Xmx` appropriately
- Enable container memory limits
- Configure Prometheus `process_resident_memory_bytes` alert at 85%
