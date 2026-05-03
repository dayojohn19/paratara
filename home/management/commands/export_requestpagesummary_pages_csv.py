from __future__ import annotations

import csv
from collections import defaultdict
from typing import Any

from django.core.management.base import BaseCommand

from home.models import RequestPageSummary


def _iter_pages(pages_json: Any):
    """Yield (page, count) pairs from pages_json.

    Expected shape is a dict like {"/some/page": 12, ...}.
    Falls back gracefully for odd/legacy shapes.
    """
    if not pages_json:
        return

    if isinstance(pages_json, dict):
        for page, count in pages_json.items():
            if page is None:
                continue
            page_str = str(page)
            # count can be int-like, string, None, etc.
            try:
                count_int = int(count)
            except Exception:
                count_int = 1
            yield page_str, max(count_int, 0)
        return

    # If it was stored as a list of pages, treat each as 1
    if isinstance(pages_json, (list, tuple, set)):
        for page in pages_json:
            if page is None:
                continue
            yield str(page), 1
        return

    # If it's a string blob, not much we can do reliably; ignore.
    return


class Command(BaseCommand):
    help = (
        "Export aggregated page stats from RequestPageSummary.pages_json into a CSV. "
        "Outputs per-page totals and how many RequestPageSummary rows contained that page."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default="requestpagesummary_pages.csv",
            help="Output CSV path (default: requestpagesummary_pages.csv).",
        )
        parser.add_argument(
            "--progress-every",
            type=int,
            default=5000,
            help="Print progress every N RequestPageSummary rows (default: 5000). Use 0 to disable.",
        )
        parser.add_argument(
            "--order-by",
            choices=["total_requests", "ip_count", "page"],
            default="total_requests",
            help="Sort order for CSV rows (default: total_requests).",
        )

    def handle(self, *args, **options):
        out_path = str(options.get("out") or "requestpagesummary_pages.csv")
        progress_every = int(options.get("progress_every") or 0)
        if progress_every < 0:
            progress_every = 0

        order_by = str(options.get("order_by") or "total_requests")

        total_rows = RequestPageSummary.objects.count()
        processed = 0

        # page -> sum of counts across all summaries
        total_requests_by_page: dict[str, int] = defaultdict(int)
        # page -> how many summaries contained it (unique IP occurrences)
        ip_count_by_page: dict[str, int] = defaultdict(int)

        qs = RequestPageSummary.objects.all().only("id", "pages_json")

        for summary in qs.iterator(chunk_size=500):
            processed += 1

            seen_pages_in_this_summary: set[str] = set()
            for page, count in _iter_pages(summary.pages_json):
                total_requests_by_page[page] += int(count)
                seen_pages_in_this_summary.add(page)

            for page in seen_pages_in_this_summary:
                ip_count_by_page[page] += 1

            if progress_every and (processed % progress_every == 0):
                pct = (processed / total_rows * 100.0) if total_rows else 100.0
                self.stdout.write(f"Progress: {processed}/{total_rows} ({pct:.1f}%)")

        rows = []
        for page, total in total_requests_by_page.items():
            rows.append(
                {
                    "page": page,
                    "total_requests": int(total),
                    "ip_count": int(ip_count_by_page.get(page, 0)),
                }
            )

        if order_by == "page":
            rows.sort(key=lambda r: (r["page"] or "").lower())
        elif order_by == "ip_count":
            rows.sort(key=lambda r: (-r["ip_count"], -r["total_requests"], (r["page"] or "").lower()))
        else:  # total_requests
            rows.sort(key=lambda r: (-r["total_requests"], -r["ip_count"], (r["page"] or "").lower()))

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["page", "total_requests", "ip_count"])
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(f"Wrote {len(rows)} rows to {out_path}"))
