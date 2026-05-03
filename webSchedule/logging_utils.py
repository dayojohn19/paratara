import time
import logging
from django.utils.log import ServerFormatter


class SafeServerFormatter(ServerFormatter):
    """A ServerFormatter that guarantees `record.server_time` exists.

    This prevents formatting errors when a log record is emitted from
    code paths that do not already set `server_time` (e.g., during
    connection resets or early error handling).
    """

    def format(self, record):
        try:
            if not hasattr(record, "server_time"):
                # This mirrors the format used by Django's ServerFormatter
                record.server_time = time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            record.server_time = ""
        return super().format(record)
