#!/usr/bin/env python3
"""
PostgreSQL Backup to Mega Cloud Script

Creates compressed backups of PostgreSQL database and uploads to Mega cloud storage
with automatic retention policy enforcement.

Usage:
    python backup-to-mega.py

Environment Variables:
    POSTGRES_HOST: Database host (default: localhost)
    POSTGRES_PORT: Database port (default: 5432)
    POSTGRES_USER: Database user (default: goalixa)
    POSTGRES_PASSWORD: Database password (required)
    POSTGRES_DB: Database name (default: goalixa)
    MEGA_EMAIL: Mega account email (required)
    MEGA_PASSWORD: Mega account password (required)
    BACKUP_RETENTION_DAYS: Days of daily backups to keep (default: 7)
    BACKUP_RETENTION_WEEKS: Weeks of weekly backups to keep (default: 4)
    BACKUP_RETENTION_MONTHS: Months of monthly backups to keep (default: 3)
    MEGA_BACKUP_PATH: Remote Mega path for backups (default: /goalixa-backups)
"""

import os
import sys
import subprocess
import logging
import tempfile
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
import re

try:
    from mega import Mega
    MEGA_SDK_AVAILABLE = True
except ImportError:
    MEGA_SDK_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class MegaBackupManager:
    """Manages PostgreSQL backups and Mega cloud uploads."""

    def __init__(self):
        """Initialize backup manager with environment variables."""
        self.postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        self.postgres_port = os.getenv('POSTGRES_PORT', '5432')
        self.postgres_user = os.getenv('POSTGRES_USER', 'goalixa')
        self.postgres_password = os.getenv('POSTGRES_PASSWORD')
        self.postgres_db = os.getenv('POSTGRES_DB', 'goalixa')

        self.mega_email = os.getenv('MEGA_EMAIL')
        self.mega_password = os.getenv('MEGA_PASSWORD')
        self.mega_backup_path = os.getenv('MEGA_BACKUP_PATH', '/goalixa-backups')

        self.retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '7'))
        self.retention_weeks = int(os.getenv('BACKUP_RETENTION_WEEKS', '4'))
        self.retention_months = int(os.getenv('BACKUP_RETENTION_MONTHS', '3'))

        self.temp_dir = tempfile.mkdtemp(prefix='goalixa_backup_')
        self.mega_client = None
        self.use_mega_cli = not MEGA_SDK_AVAILABLE

        logger.info("Backup manager initialized")
        logger.info(f"Database: {self.postgres_user}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}")
        logger.info(f"Mega path: {self.mega_backup_path}")
        logger.info(f"Retention: {self.retention_days} daily, {self.retention_weeks} weekly, {self.retention_months} monthly")
        if MEGA_SDK_AVAILABLE:
            logger.info("Using Mega Python SDK")
        else:
            logger.info("Using Mega CLI tools (megatools)")

    def validate_config(self) -> bool:
        """Validate required configuration."""
        required = ['POSTGRES_PASSWORD', 'MEGA_EMAIL', 'MEGA_PASSWORD']
        missing = [v for v in required if not os.getenv(v)]

        if missing:
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            return False

        return True

    def create_backup(self) -> Optional[str]:
        """
        Create compressed PostgreSQL backup.

        Returns:
            Path to backup file or None on failure
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"goalixa_{timestamp}.sql.gz"
        backup_path = os.path.join(self.temp_dir, backup_name)

        logger.info(f"Creating backup: {backup_name}")

        env = os.environ.copy()
        env['PGPASSWORD'] = self.postgres_password

        try:
            # Create uncompressed dump
            dump_path = backup_path.replace('.gz', '')
            with open(dump_path, 'w') as dump_file:
                result = subprocess.run(
                    [
                        'pg_dump',
                        '-h', self.postgres_host,
                        '-p', self.postgres_port,
                        '-U', self.postgres_user,
                        '-d', self.postgres_db,
                        '--no-password'
                    ],
                    env=env,
                    stdout=dump_file,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=300
                )

            if result.returncode != 0:
                logger.error(f"pg_dump failed: {result.stderr}")
                return None

            # Check dump file size
            dump_size = os.path.getsize(dump_path)
            if dump_size == 0:
                logger.error("Backup dump is empty")
                return None

            logger.info(f"Dump created: {dump_size:,} bytes")

            # Compress with gzip level 9
            logger.info("Compressing backup...")
            with open(dump_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb', compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove uncompressed dump
            os.remove(dump_path)

            compressed_size = os.path.getsize(backup_path)
            ratio = (1 - compressed_size / dump_size) * 100
            logger.info(f"Compressed: {compressed_size:,} bytes ({ratio:.1f}% reduction)")

            return backup_path

        except subprocess.TimeoutExpired:
            logger.error("Backup creation timed out")
            return None
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return None

    def mega_login(self) -> bool:
        """Login to Mega account."""
        logger.info(f"Logging in to Mega: {self.mega_email}")

        try:
            if MEGA_SDK_AVAILABLE:
                # Use Python SDK
                self.mega_client = Mega()
                self.mega_client.login(self.mega_email, self.mega_password)
                logger.info("Logged in to Mega successfully (SDK)")
                return True
            else:
                # Use CLI
                result = subprocess.run(
                    ['mega-login', self.mega_email, self.mega_password],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode != 0:
                    logger.error(f"Mega login failed: {result.stderr}")
                    return False

                logger.info("Logged in to Mega successfully (CLI)")
                return True

        except Exception as e:
            logger.error(f"Mega login error: {e}")
            return False

    def mega_upload(self, backup_path: str) -> bool:
        """
        Upload backup to Mega.

        Args:
            backup_path: Local path to backup file

        Returns:
            True on success, False on failure
        """
        backup_name = os.path.basename(backup_path)
        logger.info(f"Uploading to Mega: {backup_name}")

        try:
            if MEGA_SDK_AVAILABLE and self.mega_client:
                # Use Python SDK
                try:
                    # Create backup folder if it doesn't exist
                    try:
                        folder = self.mega_client.find(self.mega_backup_path)
                        if not folder:
                            self.mega_client.create_folder(self.mega_backup_path)
                            folder = self.mega_client.find(self.mega_backup_path)
                    except:
                        self.mega_client.create_folder(self.mega_backup_path)
                        folder = self.mega_client.find(self.mega_backup_path)

                    # Upload file
                    self.mega_client.upload(backup_path, folder[0])
                    logger.info(f"Uploaded successfully: {self.mega_backup_path}/{backup_name}")
                    return True
                except Exception as e:
                    logger.error(f"SDK upload failed: {e}")
                    return False
            else:
                # Use CLI
                result = subprocess.run(
                    ['mega-put', backup_path, f"{self.mega_backup_path}/{backup_name}"],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode != 0:
                    logger.error(f"Mega upload failed: {result.stderr}")
                    return False

                logger.info(f"Uploaded successfully: {self.mega_backup_path}/{backup_name}")
                return True

        except subprocess.TimeoutExpired:
            logger.error("Upload timed out")
            return False
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False

    def mega_logout(self) -> bool:
        """Logout from Mega."""
        try:
            subprocess.run(['mega-logout'], capture_output=True, timeout=10)
            logger.info("Logged out from Mega")
            return True
        except Exception as e:
            logger.warning(f"Logout warning: {e}")
            return True  # Don't fail on logout

    def get_remote_backups(self) -> List[str]:
        """
        List backup files in Mega.

        Returns:
            List of backup filenames
        """
        logger.info(f"Listing backups in {self.mega_backup_path}")

        try:
            result = subprocess.run(
                ['mega-ls', '-l', self.mega_backup_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.warning(f"Failed to list remote backups: {result.stderr}")
                return []

            # Parse mega-ls output: lines like "FILE  1234  Oct 01 12:34 goalixa_20260501_143000.sql.gz"
            backups = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and 'goalixa_' in line and '.sql.gz' in line:
                    # Extract filename
                    parts = line.split()
                    if len(parts) >= 4:
                        filename = parts[-1]
                        backups.append(filename)

            backups.sort()
            logger.info(f"Found {len(backups)} remote backups")
            return backups

        except Exception as e:
            logger.warning(f"Error listing remote backups: {e}")
            return []

    def parse_backup_date(self, filename: str) -> Optional[datetime]:
        """
        Parse backup filename to extract timestamp.

        Args:
            filename: Backup filename (goalixa_YYYYMMDD_HHMMSS.sql.gz)

        Returns:
            datetime object or None
        """
        match = re.match(r'goalixa_(\d{8})_(\d{6})\.sql\.gz', filename)
        if match:
            date_str = f"{match.group(1)}{match.group(2)}"
            try:
                return datetime.strptime(date_str, "%Y%m%d%H%M%S")
            except ValueError:
                return None
        return None

    def get_backups_to_delete(self, backups: List[str]) -> List[str]:
        """
        Determine which backups to delete based on retention policy.

        Args:
            backups: List of backup filenames

        Returns:
            List of filenames to delete
        """
        logger.info("Applying retention policy...")

        # Parse all backups with dates
        backup_dates = []
        for backup in backups:
            date = self.parse_backup_date(backup)
            if date:
                backup_dates.append((backup, date))

        if not backup_dates:
            return []

        # Sort by date
        backup_dates.sort(key=lambda x: x[1])

        # Keep last N daily backups
        now = datetime.now()
        keep_set = set()

        # Daily: keep last N days
        for backup, date in backup_dates[-self.retention_days:]:
            keep_set.add(backup)

        # Weekly: keep first backup of each week (last 4 weeks)
        weekly = {}
        for backup, date in backup_dates:
            week_key = date.isocalendar()[1]  # ISO week number
            if week_key not in weekly:
                weekly[week_key] = (backup, date)

        for backup, date in list(weekly.values())[-self.retention_weeks:]:
            keep_set.add(backup)

        # Monthly: keep first backup of each month (last 3 months)
        monthly = {}
        for backup, date in backup_dates:
            month_key = date.strftime("%Y-%m")
            if month_key not in monthly:
                monthly[month_key] = (backup, date)

        for backup, date in list(monthly.values())[-self.retention_months:]:
            keep_set.add(backup)

        # Determine deletions
        to_delete = [b for b in backups if b not in keep_set]

        logger.info(f"Keeping {len(keep_set)} backups, deleting {len(to_delete)}")
        for backup in to_delete:
            logger.info(f"  - {backup}")

        return to_delete

    def delete_old_backups(self, backups_to_delete: List[str]) -> bool:
        """
        Delete old backups from Mega.

        Args:
            backups_to_delete: List of filenames to delete

        Returns:
            True if all deletions succeeded
        """
        if not backups_to_delete:
            logger.info("No backups to delete")
            return True

        logger.info(f"Deleting {len(backups_to_delete)} old backups...")

        all_success = True
        for backup in backups_to_delete:
            try:
                result = subprocess.run(
                    ['mega-rm', f"{self.mega_backup_path}/{backup}"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode != 0:
                    logger.warning(f"Failed to delete {backup}: {result.stderr}")
                    all_success = False
                else:
                    logger.info(f"Deleted: {backup}")

            except Exception as e:
                logger.warning(f"Error deleting {backup}: {e}")
                all_success = False

        return all_success

    def cleanup(self):
        """Clean up temporary files."""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info("Cleaned up temporary files")
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")

    def run(self) -> int:
        """
        Run the backup process.

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            # Validate configuration
            if not self.validate_config():
                return 1

            # Create backup
            backup_path = self.create_backup()
            if not backup_path:
                return 1

            # Login to Mega
            if not self.mega_login():
                return 1

            # Upload backup
            if not self.mega_upload(backup_path):
                self.mega_logout()
                return 1

            # Get remote backups and apply retention
            remote_backups = self.get_remote_backups()
            if remote_backups:
                to_delete = self.get_backups_to_delete(remote_backups)
                self.delete_old_backups(to_delete)

            # Logout
            self.mega_logout()

            logger.info("SUCCESS: Backup completed successfully")
            return 0

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return 1
        finally:
            self.cleanup()


def main():
    """Main entry point."""
    manager = MegaBackupManager()
    exit_code = manager.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
