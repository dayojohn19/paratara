#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import warnings


# Django's autoreloader runs a parent + child process. When using urllib3 v2 with
# a LibreSSL-backed Python build, urllib3 emits a startup warning; the reloader
# causes it to appear twice. Filter it in the parent so it's shown only once.
if os.environ.get("RUN_MAIN") != "true":
    warnings.filterwarnings(
        "ignore",
        message=r"urllib3 v2 only supports OpenSSL 1\.1\.1\+.*",
        category=Warning,
        module=r"urllib3(\..*)?",
    )


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webSchedule.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
