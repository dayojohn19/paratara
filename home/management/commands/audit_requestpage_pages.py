from __future__ import annotations

from collections import Counter, defaultdict
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models import Q
from django.urls import Resolver404, resolve

from home.models import RequestPage


class Command(BaseCommand):
    help = (
        "Check RequestPage.page_name values and count which would be 404 vs non-404. "
        "Fast by default (URL resolver). Optional --http uses Django test Client."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--http",
            action="store_true",
            help=(
                "Actually GET each page via Django's test Client and use the real status_code. "
                "Slower than resolver mode."
            ),
        )
        parser.add_argument(
            "--top",
            type=int,
            default=30,
            help="Show top N 404 pages by row count (default: 30)",
        )
        parser.add_argument(
            "--delete-404",
            action="store_true",
            help="Delete RequestPage rows whose page_name is detected as 404 (asks for confirmation unless --force).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation prompt for --delete-404.",
        )
        parser.add_argument(
            "--print-delete-limit",
            type=int,
            default=50,
            help="When using --delete-404, print up to N page_name values that will be deleted (default: 50; 0 to disable).",
        )
        parser.add_argument(
            "--delete-localhost",
            action="store_true",
            help="Delete RequestPage rows where requesting_ip is localhost (127.*). Uses confirmation unless --force.",
        )

    def handle(self, *args, **options):
        use_http = bool(options["http"])
        top_n = int(options["top"])
        delete_404 = bool(options["delete_404"])
        force = bool(options["force"])
        print_delete_limit = int(options["print_delete_limit"])
        delete_localhost = bool(options["delete_localhost"])

        grouped = (
            RequestPage.objects.values("page_name")
            .annotate(row_count=Count("id"))
            .order_by()
        )

        cache_status = {}

        records_404 = 0
        records_not_404 = 0
        records_empty = 0
        records_error = 0

        status_counter_unique = Counter()
        status_counter_records = Counter()

        examples = defaultdict(list)  # status -> [paths]
        top_404_counts = Counter()  # path -> records referencing it
        raw_404_counts = Counter()  # raw page_name -> records referencing it
        raw_pages_to_delete = set()

        if use_http:
            from django.test import Client

            client = Client()

        for row in grouped.iterator(chunk_size=2000):
            raw_page = (row.get("page_name") or "").strip()
            row_count = int(row.get("row_count") or 0)

            if not raw_page:
                records_empty += row_count
                status_counter_unique["EMPTY"] += 1
                status_counter_records["EMPTY"] += row_count
                continue

            path, path_and_query = self._normalize_to_path(raw_page)
            cache_key = path_and_query if use_http else path

            if cache_key not in cache_status:
                try:
                    if use_http:
                        resp = client.get(path_and_query)
                        status = getattr(resp, "status_code", None)
                    else:
                        resolve(path)
                        status = "OK"
                except Resolver404:
                    status = 404
                except Exception:
                    status = "ERROR"

                cache_status[cache_key] = status
                status_counter_unique[status] += 1
                if len(examples[status]) < 10:
                    examples[status].append(path_and_query)

            status = cache_status[cache_key]
            status_counter_records[status] += row_count

            if status == 404:
                records_404 += row_count
                top_404_counts[path_and_query] += row_count
                raw_404_counts[raw_page] += row_count
                if delete_404:
                    raw_pages_to_delete.add(raw_page)
            elif status == "ERROR":
                records_error += row_count
            else:
                records_not_404 += row_count

        total_records = RequestPage.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f"=== RequestPage.page_name 404 check ({'HTTP' if use_http else 'resolver'} mode) ==="
            )
        )
        self.stdout.write(f"Total RequestPage records: {total_records}")
        self.stdout.write(f"Unique page_names checked: {len(cache_status)}")
        self.stdout.write("")

        self.stdout.write(self.style.ERROR(f"Records that are 404:      {records_404}"))
        self.stdout.write(self.style.SUCCESS(f"Records not 404:          {records_not_404}"))
        if records_empty:
            self.stdout.write(self.style.WARNING(f"Records with empty page:   {records_empty}"))
        if records_error:
            self.stdout.write(self.style.WARNING(f"Records with errors:       {records_error}"))

        self.stdout.write("")
        self.stdout.write("-- Unique page status counts --")
        for status, count in status_counter_unique.most_common():
            self.stdout.write(f"{str(status):>7}: {count}")

        self.stdout.write("")
        self.stdout.write("-- Record status counts (weighted by rows) --")
        for status, count in status_counter_records.most_common():
            self.stdout.write(f"{str(status):>7}: {count}")

        if top_n > 0:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(f"-- Top {top_n} 404 pages (by RequestPage row count) --"))
            for page, count in top_404_counts.most_common(top_n):
                self.stdout.write(f"{count:>7}  http://127.0.0.1:8000{page}")

        self.stdout.write("")
        self.stdout.write("-- Example pages by status (up to 10 each) --")
        for status, pages in sorted(examples.items(), key=lambda kv: str(kv[0])):
            self.stdout.write(f"\nStatus {status}:")
            for p in pages:
                self.stdout.write(f"  {p}")

        if delete_404:
            self._delete_404_rows(
                raw_pages_to_delete=raw_pages_to_delete,
                raw_404_counts=raw_404_counts,
                force=force,
                use_http=use_http,
                print_delete_limit=print_delete_limit,
            )

        if delete_localhost:
            self._delete_localhost_rows(force=force, print_delete_limit=print_delete_limit)

    def _delete_localhost_rows(self, *, force: bool, print_delete_limit: int) -> None:
        localhost_q = Q(requesting_ip__startswith="127.")
        qs = RequestPage.objects.filter(localhost_q)
        to_delete_count = qs.count()

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("=== DELETE LOCALHOST REQUESTPAGE ROWS ==="))
        self.stdout.write("Match: requesting_ip starts with 127.")
        self.stdout.write(f"Total RequestPage rows to delete:  {to_delete_count}")

        if to_delete_count == 0:
            self.stdout.write(self.style.WARNING("No localhost RequestPage rows found."))
            return

        if print_delete_limit != 0:
            limit = max(0, int(print_delete_limit))
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Example localhost pages (top by count):"))
            grouped_local = (
                RequestPage.objects.filter(localhost_q)
                .values("page_name")
                .annotate(row_count=Count("id"))
                .order_by("-row_count")
            )
            shown = 0
            for row in grouped_local.iterator(chunk_size=2000):
                self.stdout.write(f"  {int(row['row_count']):>7}  {row['page_name']}")
                shown += 1
                if shown >= limit:
                    break
            remaining = grouped_local.count() - shown
            if remaining > 0:
                self.stdout.write(self.style.WARNING(f"  ... ({remaining} more not shown; use --print-delete-limit to increase)"))

        if not force:
            confirm = input('Type "yes" to delete these localhost RequestPage rows: ')
            if confirm.strip().lower() != "yes":
                self.stdout.write(self.style.ERROR("Deletion cancelled."))
                return

        deleted_count, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} RequestPage rows (localhost)."))

    def _delete_404_rows(
        self,
        *,
        raw_pages_to_delete: set[str],
        raw_404_counts: Counter,
        force: bool,
        use_http: bool,
        print_delete_limit: int,
    ) -> None:
        if not raw_pages_to_delete:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("--delete-404: No 404 pages detected; nothing to delete."))
            return

        qs = RequestPage.objects.filter(page_name__in=raw_pages_to_delete)
        to_delete_count = qs.count()

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("=== DELETE 404 REQUESTPAGE ROWS ==="))
        self.stdout.write(f"Mode: {'HTTP' if use_http else 'resolver'}")
        self.stdout.write(f"Unique page_name values to delete: {len(raw_pages_to_delete)}")
        self.stdout.write(f"Total RequestPage rows to delete:  {to_delete_count}")

        if print_delete_limit != 0:
            limit = max(0, int(print_delete_limit))
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Will delete these page_name values (top by count):"))
            shown = 0
            for page_name, cnt in raw_404_counts.most_common():
                if page_name not in raw_pages_to_delete:
                    continue
                self.stdout.write(f"  {cnt:>7}  {page_name}")
                shown += 1
                if shown >= limit:
                    break
            remaining = len(raw_pages_to_delete) - shown
            if remaining > 0:
                self.stdout.write(self.style.WARNING(f"  ... ({remaining} more not shown; use --print-delete-limit to increase)"))

        if to_delete_count == 0:
            self.stdout.write(self.style.WARNING("Nothing matched for deletion (already deleted?)"))
            return

        if not force:
            confirm = input('Type "yes" to delete these RequestPage rows: ')
            if confirm.strip().lower() != "yes":
                self.stdout.write(self.style.ERROR("Deletion cancelled."))
                return

        deleted_count, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} RequestPage rows."))

    def _normalize_to_path(self, raw_page: str) -> tuple[str, str]:
        """Return (path, path_and_query) from either a raw path or a full URL."""
        parsed = urlparse(raw_page)
        if parsed.scheme and parsed.netloc:
            path = parsed.path or "/"
            query = parsed.query
        else:
            path = raw_page
            query = ""

        if not path.startswith("/"):
            path = "/" + path

        path_and_query = path + ("?" + query if query else "")
        return path, path_and_query
