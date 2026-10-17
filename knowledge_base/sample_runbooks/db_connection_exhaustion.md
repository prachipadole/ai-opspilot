# Runbook: Database Connection Pool Exhaustion

## Symptoms
- Application logs show `OperationalError: too many connections`
- `pg_stat_activity` shows connections at or near `max_connections`
- Increased query latency or timeouts

## Root Cause Categories
1. **Missing connection pooling** (PgBouncer / SQLAlchemy pool)
2. **Connection leak** — connections not returned to pool
3. **Sudden traffic spike** overwhelming the pool
4. **Long-running transactions** holding connections

## Diagnosis Steps

```sql
-- Active connections by state
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;

-- Longest running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > INTERVAL '5 minutes';

-- Check max_connections setting
SHOW max_connections;
```

```bash
# PgBouncer pool stats
psql -h 127.0.0.1 -p 6432 pgbouncer -c "SHOW POOLS;"
```

## Remediation

### Option A – Terminate idle connections
```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND query_start < NOW() - INTERVAL '10 minutes';
```

### Option B – Increase pool size temporarily
```bash
# SQLAlchemy pool_size + max_overflow via env
export DB_POOL_SIZE=20
export DB_MAX_OVERFLOW=30
systemctl restart app
```

### Option C – Deploy PgBouncer
Deploy PgBouncer in transaction pooling mode in front of PostgreSQL.

## Prevention
- Always use a connection pool (PgBouncer or SQLAlchemy)
- Set `pool_timeout` and `pool_recycle` on the application side
- Alert when `pg_stat_activity` count > 80% of `max_connections`
