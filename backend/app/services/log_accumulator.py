"""Service for accumulating text logs to daily log files."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class LogAccumulator:
    """Accumulates text logs into daily .log files."""

    def __init__(self, analysis_dir: str):
        """Initialize log accumulator.

        Args:
            analysis_dir: Base directory for analysis files
        """
        self.analysis_dir = Path(analysis_dir)
        self._ensure_base_directory()

    def _ensure_base_directory(self):
        """Ensure base analysis directory exists."""
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Analysis directory: {self.analysis_dir}")

    def get_daily_log_path(self, date: str) -> Path:
        """Get path to daily log file for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Path to daily.log file
        """
        date_dir = self.analysis_dir / date
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir / "daily.log"

    def append_text_log(
        self,
        text: str,
        app_package: str,
        timestamp: int,
        device_id: Optional[str] = None
    ) -> None:
        """Append a text log entry to the appropriate daily log file.

        Args:
            text: Captured text content
            app_package: Source app package name
            timestamp: Timestamp in milliseconds
            device_id: Optional device identifier
        """
        try:
            # Convert timestamp to date
            dt = datetime.fromtimestamp(timestamp / 1000.0)
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")

            # Get log file path
            log_path = self.get_daily_log_path(date_str)

            # Format log entry
            # Format: [HH:MM:SS] [app.package.name] Text content here
            log_entry = f"[{time_str}] [{app_package}] {text}\n"

            # Append to log file (atomic write not needed for append)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)

            logger.debug(f"Appended log to {log_path}: {app_package}")

        except Exception as e:
            logger.error(f"Failed to append log: {e}", exc_info=True)
            # Don't raise - log accumulation should not break the main flow

    def append_text_logs_batch(
        self,
        logs: list[dict]
    ) -> int:
        """Append multiple text logs at once.

        Args:
            logs: List of log dictionaries with keys: text, appPackage, timestamp, deviceId

        Returns:
            Number of logs successfully appended
        """
        success_count = 0

        for log in logs:
            try:
                self.append_text_log(
                    text=log.get("text", ""),
                    app_package=log.get("appPackage", "unknown"),
                    timestamp=log.get("timestamp", 0),
                    device_id=log.get("deviceId")
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to append log in batch: {e}")
                continue

        logger.info(f"Appended {success_count}/{len(logs)} logs to daily files")
        return success_count

    def get_log_content(self, date: str) -> Optional[str]:
        """Read the entire log file for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Log file content, or None if file doesn't exist
        """
        log_path = self.get_daily_log_path(date)

        if not log_path.exists():
            logger.warning(f"No log file found for {date}")
            return None

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"Failed to read log file {log_path}: {e}")
            return None

    def get_log_count(self, date: str) -> int:
        """Count number of log entries for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Number of log entries (lines in file)
        """
        content = self.get_log_content(date)
        if not content:
            return 0

        # Count non-empty lines
        return len([line for line in content.split("\n") if line.strip()])

    def get_date_range_logs(self, start_date: str, end_date: str) -> dict[str, str]:
        """Get all log files for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dictionary mapping date -> log content
        """
        from datetime import timedelta

        logs = {}
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            content = self.get_log_content(date_str)
            if content:
                logs[date_str] = content
            current_dt += timedelta(days=1)

        return logs

    def create_weekly_log_file(self, start_date: str, end_date: str) -> Path:
        """Create a combined weekly log file from daily logs.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Path to created weekly log file
        """
        # Create weekly directory
        weekly_dir = self.analysis_dir / f"{start_date}_to_{end_date}"
        weekly_dir.mkdir(parents=True, exist_ok=True)
        weekly_log_path = weekly_dir / "weekly.log"

        # Get all daily logs
        daily_logs = self.get_date_range_logs(start_date, end_date)

        # Combine into weekly log
        with open(weekly_log_path, "w", encoding="utf-8") as f:
            for date in sorted(daily_logs.keys()):
                f.write(f"\n{'='*60}\n")
                f.write(f"Date: {date}\n")
                f.write(f"{'='*60}\n\n")
                f.write(daily_logs[date])
                f.write("\n")

        logger.info(f"Created weekly log at {weekly_log_path}")
        return weekly_log_path
