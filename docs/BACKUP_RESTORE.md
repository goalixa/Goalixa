# Goalixa Database Backup & Restore Documentation

## Overview

This document describes the automated backup system for the Goalixa PostgreSQL database. Backups are created daily, compressed with gzip, and uploaded to Mega cloud storage with automatic retention policy enforcement.

## Architecture

### Backup Flow

```
PostgreSQL Database
         ↓
   pg_dump SQL
         ↓
   gzip compression (level 9)
         ↓
   Mega Cloud Upload
         ↓
   Retention Policy Enforcement
```

### Components

1. **backup-to-mega.py** - Python script that orchestrates the backup process
2. **Dockerfile.backup** - Docker image with PostgreSQL client and megatools
3. **CronJob** - Kubernetes scheduled backup job (runs daily at 2 AM UTC)
4. **ExternalSecret** - Syncs Mega credentials from Vault
5. **restore-from-mega.sh** - Shell script for manual restores

## Quick Start

### Deploy Backup System

#### 1. Store Mega Credentials in Vault

```bash
# Login to Vault
export VAULT_ADDR=https://vault.goalixa.com
vault login

# Create/update secret
vault kv put goalixa/backup/mega-credentials \
  MEGA_EMAIL="your-mega-email@example.com" \
  MEGA_PASSWORD="your-mega-password"

# Verify
vault kv get goalixa/backup/mega-credentials
```

#### 2. Build and Push Docker Image

```bash
cd Core-API

# Build image
docker build -f Dockerfile.backup \
  -t harbor.goalixa.com/goalixa/backup:1.0.0 .

# Push to Harbor
docker push harbor.goalixa.com/goalixa/backup:1.0.0
```

#### 3. Apply Kubernetes Manifests

```bash
# Create/sync ExternalSecret (syncs credentials from Vault)
kubectl apply -f k8s/backup/external-secret-mega.yaml

# Verify secret was synced
kubectl get secret mega-credentials -n goalixa-db

# Create CronJob
kubectl apply -f k8s/backup/cronjob-backup.yaml

# Verify CronJob created
kubectl get cronjob -n goalixa-db
```

### Test Backup System

#### Manual Backup Trigger

```bash
# Create a one-time job from the CronJob
kubectl create job --from=cronjob/goalixa-db-backup test-backup-1 -n goalixa-db

# Monitor execution
kubectl logs -f job/test-backup-1 -n goalixa-db

# Check job status
kubectl get job test-backup-1 -n goalixa-db -o wide
```

#### Verify Backup in Mega

1. Login to Mega web interface (https://mega.io)
2. Navigate to `/goalixa-backups` folder
3. Verify:
   - Backup file exists with current date
   - File size is reasonable (typically 2-3 MB compressed)
   - Timestamp is recent

### Manual Restore

#### Prerequisites

```bash
# Set environment variables
export POSTGRES_PASSWORD="your-db-password"
export MEGA_EMAIL="your-mega-email@example.com"
export MEGA_PASSWORD="your-mega-password"
```

#### Restore Steps

```bash
# List available backups
./Core-API/scripts/restore-from-mega.sh -f dummy-to-list --help

# Restore latest backup (example)
./Core-API/scripts/restore-from-mega.sh \
  -f goalixa_20260501_140000.sql.gz \
  -h localhost \
  -p 5432 \
  -u goalixa \
  -d goalixa

# Dry run (show what would happen without restoring)
./Core-API/scripts/restore-from-mega.sh \
  -f goalixa_20260501_140000.sql.gz \
  --dry-run
```

## Configuration

### Environment Variables

#### backup-to-mega.py

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | localhost | PostgreSQL host |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `POSTGRES_USER` | goalixa | PostgreSQL username |
| `POSTGRES_PASSWORD` | (required) | PostgreSQL password |
| `POSTGRES_DB` | goalixa | Database name to backup |
| `MEGA_EMAIL` | (required) | Mega account email |
| `MEGA_PASSWORD` | (required) | Mega account password |
| `MEGA_BACKUP_PATH` | /goalixa-backups | Remote Mega folder for backups |
| `BACKUP_RETENTION_DAYS` | 7 | Days of daily backups to keep |
| `BACKUP_RETENTION_WEEKS` | 4 | Weeks of weekly backups to keep |
| `BACKUP_RETENTION_MONTHS` | 3 | Months of monthly backups to keep |

### Retention Policy

The backup system maintains backups across three time horizons:

- **Daily**: Last 7 daily backups (~7 days of history)
- **Weekly**: 1st backup of each week for last 4 weeks (~4 weeks)
- **Monthly**: 1st backup of each month for last 3 months (~3 months)

Total retention: **~100 days of backups**

**Space calculation**:
- Current DB size: ~10 MB
- Compressed per backup: ~2-3 MB (70-80% compression)
- Full retention: ~42 MB in Mega storage
- Mega free tier: 20 GB available

### Backup Schedule

- **Frequency**: Daily
- **Time**: 2 AM UTC (adjust in CronJob spec if needed)
- **Duration**: ~30 seconds for 10MB database
- **Expected size**: 2-3 MB per backup

## Monitoring

### Check Recent Backups

```bash
# List recent CronJob executions
kubectl get jobs -n goalixa-db -l app=goalixa-backup -o wide

# View logs of latest backup
kubectl logs -n goalixa-db -l app=goalixa-backup --tail=100

# Watch real-time logs
kubectl logs -f -n goalixa-db -l app=goalixa-backup --all-containers
```

### Backup Metrics (Prometheus)

If Prometheus is configured, these metrics are available:

- `kube_cronjob_status_last_schedule_time` - Last scheduled backup time
- `kube_job_status_succeeded` - Successful backup count
- `kube_job_status_failed` - Failed backup count

### Alert Rules

Create alerts for backup failures:

```yaml
groups:
  - name: goalixa-backups
    rules:
      - alert: BackupJobFailed
        expr: |
          increase(kube_job_status_failed{job_name=~"goalixa-db-backup.*"}[1h]) > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Goalixa database backup failed"
          description: "Backup job failed. Check logs: kubectl logs -n goalixa-db -l app=goalixa-backup"

      - alert: BackupNotRunning
        expr: |
          time() - kube_cronjob_status_last_schedule_time{cronjob="goalixa-db-backup"} > 86400
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "Goalixa backup hasn't run in 24 hours"
          description: "Check CronJob status: kubectl get cronjob -n goalixa-db goalixa-db-backup"
```

## Troubleshooting

### Backup Job Failing

#### Check job status
```bash
kubectl describe job <job-name> -n goalixa-db
```

#### View logs
```bash
kubectl logs <pod-name> -n goalixa-db
```

#### Common issues:

1. **Mega login failed**
   - Verify `MEGA_EMAIL` and `MEGA_PASSWORD` in Vault
   - Check Mega account is active and not locked

2. **pg_dump connection failed**
   - Verify PostgreSQL service is running: `kubectl get svc postgres -n goalixa-db`
   - Check database credentials in `goalixa-app-db-secret`
   - Verify network connectivity between backup pod and database

3. **Disk space issues**
   - Check pod has sufficient /tmp space
   - Monitor temporary files in backup script

4. **Mega storage full**
   - Check available space in Mega
   - Verify retention policy is deleting old backups
   - Manual cleanup: login to Mega and delete old backups

### Restore Issues

#### Connection refused
```bash
# Ensure database is accessible
psql -h localhost -U goalixa -c "SELECT 1;" goalixa
```

#### Permission denied
```bash
# Verify database user has superuser or restore permissions
# Run restore as superuser or OWNER of the database
```

#### SQL syntax errors during restore
- Backup may be corrupted
- Try downloading and inspecting the SQL file manually
- Verify pg_dump version matches PostgreSQL version

## Disaster Recovery Procedures

### Full Database Loss

**RTO (Recovery Time Objective)**: 15-30 minutes
**RPO (Recovery Point Objective)**: Up to 24 hours

**Steps**:

1. Access Mega to find latest backup
2. Download and decompress backup
3. Restore to PostgreSQL
4. Restart application services
5. Verify data integrity

**Automated restore**:
```bash
# Set environment
export POSTGRES_PASSWORD="..."
export MEGA_EMAIL="..."
export MEGA_PASSWORD="..."

# Restore
./restore-from-mega.sh \
  -f goalixa_20260501_020000.sql.gz \
  -h postgres.goalixa-db.svc.cluster.local
```

### Accidental Data Deletion

**Steps**:

1. Stop Core-API to prevent new writes: `kubectl scale deployment core-api --replicas=0`
2. Create temporary restore database
3. Restore backup to temp database
4. Query specific data: `pg_dump -t table_name -d temp_db | psql -d goalixa`
5. Verify data
6. Resume Core-API: `kubectl scale deployment core-api --replicas=2`

### Corrupted Database

**Steps**:

1. Attempt PostgreSQL recovery: `REINDEX DATABASE goalixa;`
2. If recovery fails, restore from backup (see Full Database Loss above)
3. Run integrity checks post-restore

## Performance Tuning

### Backup Speed

Current backup for 10 MB database:
- Dump: ~5 seconds
- Compression: ~8 seconds (gzip level 9)
- Upload: ~10 seconds
- **Total**: ~30 seconds

### Compression Levels

For very large databases, adjust compression:

| Level | Size Reduction | Speed | Recommended |
|-------|---|---|---|
| 1 | 40% | Fast | Large DBs (>1GB) |
| 6 | 70% | Medium | Default |
| 9 | 75% | Slow | ✓ Current (small DB) |

Modify `backup-to-mega.py` line 145:
```python
with gzip.open(backup_path, 'wb', compresslevel=6) as f_out:  # Change 9 to 6
```

### Parallel Backup (Large Databases Only)

For databases >1GB, use parallel dump:

```bash
# In backup-to-mega.py, change pg_dump call:
pg_dump -F d -j 4  # 4 parallel workers
```

## Future Enhancements

1. **Point-in-Time Recovery (PITR)**
   - Enable WAL archiving to Mega
   - Restore to specific timestamp

2. **Multi-Cloud Backup**
   - Backup to both Mega and S3
   - Geographically distributed copies

3. **Encryption at Rest**
   - GPG encrypt backup before upload
   - Store encryption key in Vault

4. **Automated Verification**
   - Periodic restore to staging database
   - Automated integrity checks

5. **Dashboard**
   - Grafana dashboard for backup metrics
   - Backup history visualization

## References

- **PostgreSQL Backup**: https://www.postgresql.org/docs/current/backup.html
- **Megatools**: https://github.com/megous/megatools
- **Kubernetes CronJob**: https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/
- **External Secrets Operator**: https://external-secrets.io/

## Support

For issues or questions:

1. Check logs: `kubectl logs -n goalixa-db -l app=goalixa-backup`
2. Review this documentation
3. Check Vault secret: `vault kv get goalixa/backup/mega-credentials`
4. Verify Mega account status and storage quota

---

**Last Updated**: 2026-05-09
**Version**: 1.0.0
**Status**: Production Ready
