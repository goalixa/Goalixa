# Goalixa Database Backup - Quick Start

## TL;DR

Automated daily backups to Mega cloud storage with compression and retention policy.

## Setup (5 minutes)

### 1. Prerequisites
```bash
# Ensure you have:
# - kubectl configured
# - docker installed
# - Vault access (VAULT_ADDR, vault login done)
```

### 2. Run Setup Script
```bash
cd Core-API
chmod +x scripts/setup-backup.sh
./scripts/setup-backup.sh --all
```

This will:
- Prompt for Mega credentials (stored in Vault)
- Build and push Docker image to Harbor
- Deploy Kubernetes manifests
- Run test backup

## Manual Operations

### View Backup Status
```bash
# List all backups
kubectl get jobs -n goalixa-db -l app=goalixa-backup

# View latest backup logs
kubectl logs -n goalixa-db -l app=goalixa-backup --tail=100

# Watch real-time logs
kubectl logs -f -n goalixa-db -l app=goalixa-backup
```

### Trigger Manual Backup
```bash
kubectl create job manual-backup-$(date +%s) \
  --from=cronjob/goalixa-db-backup \
  -n goalixa-db
```

### Restore Database
```bash
cd Core-API/scripts

# Set credentials
export POSTGRES_PASSWORD="your-db-password"
export MEGA_EMAIL="your-mega-email"
export MEGA_PASSWORD="your-mega-password"

# Restore latest backup (example)
./restore-from-mega.sh \
  -f goalixa_20260509_020000.sql.gz \
  -h localhost

# Dry run (preview)
./restore-from-mega.sh \
  -f goalixa_20260509_020000.sql.gz \
  --dry-run
```

## Configuration

### Backup Schedule
Default: **Daily at 2 AM UTC**

Edit in `helm/values.yaml`:
```yaml
backup:
  schedule: "0 2 * * *"  # Cron format
```

### Retention Policy
Default:
- **7 days** of daily backups
- **4 weeks** of weekly backups (1st of week)
- **3 months** of monthly backups (1st of month)

Edit in `helm/values.yaml`:
```yaml
backup:
  retention:
    days: 7
    weeks: 4
    months: 3
```

### Storage Limits
```
Current DB size: ~10 MB
Compressed per backup: 2-3 MB
Full retention: ~42 MB
Mega free tier: 20 GB available
```

## Troubleshooting

### Check if backup ran
```bash
kubectl get jobs -n goalixa-db -o wide
```

### View error logs
```bash
kubectl logs <pod-name> -n goalixa-db
```

### Common issues

| Issue | Solution |
|-------|----------|
| Mega login failed | Verify credentials in Vault: `vault kv get goalixa/backup/mega-credentials` |
| Database connection error | Ensure PostgreSQL is running: `kubectl get svc postgres -n goalixa-db` |
| Disk space error | Check temp space: `kubectl exec -it <pod> -- df -h` |

## Reference Files

- **Backup script**: `Core-API/scripts/backup-to-mega.py`
- **Restore script**: `Core-API/scripts/restore-from-mega.sh`
- **Docker image**: `Core-API/Dockerfile.backup`
- **CronJob manifest**: `Core-API/k8s/backup/cronjob-backup.yaml`
- **Kubernetes secret**: `Core-API/k8s/backup/external-secret-mega.yaml`
- **Full documentation**: `Core-API/docs/BACKUP_RESTORE.md`

## Support

For detailed information, see `Core-API/docs/BACKUP_RESTORE.md`

---
Last Updated: 2026-05-09
