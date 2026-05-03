from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from home.models import RequestPageSummary


def _contains_php(value: Any) -> bool:
    """Return True if the JSON-ish value contains '.php' or 'wp-includes' (case-insensitive)."""
    if value is None:
        return False

    def _has_match(s: str) -> bool:
        s = s.lower()
        return ".php" in s or "wp-" in s or "upload" in s or "robots" in s
        

    if isinstance(value, str):
        return _has_match(value)

    if isinstance(value, dict):
        for key, inner in value.items():
            if isinstance(key, str) and _has_match(key):
                return True
            if isinstance(inner, str) and _has_match(inner):
                return True

            if isinstance(key, (dict, list, tuple, set)) and _contains_php(key):
                return True
            if isinstance(inner, (dict, list, tuple, set)) and _contains_php(inner):
                return True
        return False

    if isinstance(value, (list, tuple, set)):
        for inner in value:
            if _contains_php(inner):
                return True
        return False

    return False


class Command(BaseCommand):
    help = (
        "Delete RequestPageSummary rows whose pages_json contains '.php'. "
        "Print each requesting_ip deleted and a final deleted count."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print matching IPs and final count, but do not delete anything.",
        )
        parser.add_argument(
            "--print-ips",
            action="store_true",
            help="Print matching requesting_ip values after scanning (can be slow).",
        )
        parser.add_argument(
            "--delete-batch-size",
            type=int,
            default=1000,
            help="Bulk delete batch size (default: 1000).",
        )
        parser.add_argument(
            "--progress-every",
            type=int,
            default=5000,
            help="Print progress every N processed rows (default: 5000). Use 0 to disable.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        print_ips = bool(options.get("print_ips"))
        delete_batch_size = int(options.get("delete_batch_size") or 1000)
        progress_every = int(options.get("progress_every") or 0)
        if delete_batch_size < 1:
            delete_batch_size = 1000
        if progress_every < 0:
            progress_every = 0

        deleted_count = 0

        total_rows = RequestPageSummary.objects.count()
        processed = 0

        matched_ips: list[str] = []
        ids_batch: list[int] = []

        # Only fetch fields we need to keep this efficient.
        qs = RequestPageSummary.objects.all().only("id", "requesting_ip", "pages_json")

        for summary in qs.iterator(chunk_size=500):
            processed += 1
            if _contains_php(summary.pages_json):
                deleted_count += 1
                if print_ips:
                    matched_ips.append(str(summary.requesting_ip))

                if not dry_run:
                    ids_batch.append(int(summary.id))
                    if len(ids_batch) >= delete_batch_size:
                        RequestPageSummary.objects.filter(id__in=ids_batch).delete()
                        ids_batch.clear()

            if progress_every and (processed % progress_every == 0):
                pct = (processed / total_rows * 100.0) if total_rows else 100.0
                self.stdout.write(
                    f"Progress: {processed}/{total_rows} ({pct:.1f}%) | matched: {deleted_count}"
                    + (" (dry-run)" if dry_run else "")
                )

        if (not dry_run) and ids_batch:
            RequestPageSummary.objects.filter(id__in=ids_batch).delete()

        if print_ips and matched_ips:
            # Print after deletion/scan to keep the hot loop fast.
            self.stdout.write("\n".join(matched_ips))

        self.stdout.write(f"Deleted objects: {deleted_count}" + (" (dry-run)" if dry_run else ""))
