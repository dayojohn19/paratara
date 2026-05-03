from collections import defaultdict
import time

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Max, Min
from django.contrib.gis.geoip2 import GeoIP2
import os

from home.models import RequestLog, RequestPage, RequestPageSummary


class Command(BaseCommand):
    help = (
        "Summarize RequestPage rows by requesting_ip into RequestPageSummary, "
        "then delete the original RequestPage rows."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Compute and print summary counts without writing or deleting anything.",
        )
        parser.add_argument(
            "--print-each",
            action="store_true",
            help="Print a line for each IP as it is summarized (can be noisy).",
        )
        parser.add_argument(
            "--progress-every",
            type=int,
            default=100,
            help="When not using --print-each, print progress every N IPs (default: 100).",
        )
        parser.add_argument(
            "--skip-geoip",
            action="store_true",
            help="Skip GeoIP2 lookups (much faster).",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        print_each = options.get("print_each", False)
        progress_every = int(options.get("progress_every") or 100)
        skip_geoip = options.get("skip_geoip", False)
        if progress_every < 1:
            progress_every = 1

        geoip_path = getattr(settings, "GEOIP_PATH", None)
        geo_enabled = bool(geoip_path and os.path.exists(geoip_path))
        geo = GeoIP2(path=geoip_path) if (geo_enabled and not skip_geoip) else None

        total_request_pages = RequestPage.objects.count()
        if total_request_pages == 0:
            self.stdout.write(self.style.WARNING("No RequestPage rows found."))
            return

        t0 = time.time()
        self.stdout.write("\n=== RequestPage Summarizer ===")
        self.stdout.write("Phase 1/3: aggregating per-IP min/max/count...")
        ip_aggs = list(
            RequestPage.objects.values("requesting_ip")
            .annotate(
                total_requests=Count("id"),
                earliest_timesmtamp=Min("timesmtamp"),
                latest_timesmtamp=Max("timesmtamp"),
            )
            .order_by("requesting_ip")
        )

        self.stdout.write("Phase 2/3: aggregating per-IP per-page counts...")
        ip_page_counts = (
            RequestPage.objects.values("requesting_ip", "page_name")
            .annotate(count=Count("id"))
            .order_by("requesting_ip", "page_name")
        )

        pages_by_ip: dict[str, dict[str, int]] = defaultdict(dict)
        for row in ip_page_counts:
            pages_by_ip[row["requesting_ip"]][row["page_name"]] = int(row["count"])

        self.stdout.write(
            f"Found {len(ip_aggs)} IPs across {total_request_pages} RequestPage rows."
        )
        if skip_geoip:
            self.stdout.write(self.style.WARNING("GeoIP2 lookup skipped (--skip-geoip)."))
        elif geo is None:
            self.stdout.write(
                self.style.WARNING(
                    "GeoIP2 lookup disabled (GEOIP_PATH missing/invalid). Location fields will be empty."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("GeoIP2 lookup enabled."))

        self.stdout.write(f"Prep finished in {time.time() - t0:.2f}s")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no changes will be made."))
            sample = ip_aggs[:5]
            for row in sample:
                ip = row["requesting_ip"]
                pages = pages_by_ip.get(ip, {})
                self.stdout.write(
                    f"- {ip}: {row['total_requests']} req, {len(pages)} pages, "
                    f"{row['earliest_timesmtamp']} -> {row['latest_timesmtamp']}"
                )
            if len(ip_aggs) > 5:
                self.stdout.write(f"(showing 5/{len(ip_aggs)} IPs)")
            return

        created_or_updated = 0
        deleted_request_pages = 0

        ips = [row["requesting_ip"] for row in ip_aggs]
        existing_summaries = RequestPageSummary.objects.filter(requesting_ip__in=ips)
        existing_by_ip = {s.requesting_ip: s for s in existing_summaries}

        to_create: list[RequestPageSummary] = []
        to_update: list[RequestPageSummary] = []

        t3 = time.time()
        with transaction.atomic():
            total_ips = len(ip_aggs)
            self.stdout.write("Phase 3/3: writing summaries and deleting RequestPage rows...")
            for idx, row in enumerate(ip_aggs, start=1):
                ip = row["requesting_ip"]
                pages = pages_by_ip.get(ip, {})

                if print_each:
                    self.stdout.write(
                        f"\n[{idx}/{total_ips}] IP={ip} | {row['total_requests']} requests | {len(pages)} unique pages"
                    )

                ip_location_json = None
                city = None
                country_name = None
                continent_name = None

                existing = existing_by_ip.get(ip)
                # If we already have a summary with location, don't redo GeoIP work.
                if existing is not None:
                    ip_location_json = existing.ip_location_json
                    city = existing.city
                    country_name = getattr(existing, "country_name", None)
                    continent_name = getattr(existing, "continent_name", None)

                need_geo = (
                    geo is not None
                    and (existing is None or (not city and not country_name and not continent_name and not ip_location_json))
                )

                if need_geo:
                    if print_each:
                        self.stdout.write(f"  - GeoIP: looking up city/country...")
                    try:
                        try:
                            city_data = geo.city(ip)
                        except Exception as e:
                            city_data = {"error": str(e)}

                        try:
                            country_data = geo.country(ip)
                        except Exception as e:
                            country_data = {"error": str(e)}

                        ip_location_json = {
                            "city_info": city_data,
                            "country_info": country_data,
                        }

                        if isinstance(city_data, dict) and "error" not in city_data:
                            city = city_data.get("city")
                            country_name = city_data.get("country_name") or country_data.get("country_name")
                            continent_name = city_data.get("continent_name")
                            if print_each:
                                self.stdout.write(
                                    f"  - GeoIP: continent={continent_name or 'N/A'} country={country_name or 'N/A'} city={city or 'N/A'}"
                                )
                        elif print_each and isinstance(city_data, dict) and "error" in city_data:
                            self.stdout.write(f"  - GeoIP(city) error: {city_data.get('error')}")
                        if print_each and isinstance(country_data, dict) and "error" in country_data:
                            self.stdout.write(f"  - GeoIP(country) error: {country_data.get('error')}")
                    except Exception as e:
                        ip_location_json = {"error": str(e)}
                        if print_each:
                            self.stdout.write(f"  - GeoIP fatal error: {e}")
                elif print_each:
                    if skip_geoip:
                        self.stdout.write("  - GeoIP: skipped (--skip-geoip)")
                    elif geo is None:
                        self.stdout.write("  - GeoIP: skipped (GEOIP_PATH missing/invalid)")
                    else:
                        self.stdout.write("  - GeoIP: skipped (already has location)")

                if print_each:
                    self.stdout.write("  - Summary: queueing save...")

                if existing is None:
                    to_create.append(
                        RequestPageSummary(
                            requesting_ip=ip,
                            ip_location_json=ip_location_json,
                            city=city,
                            country_name=country_name,
                            continent_name=continent_name,
                            pages_json=pages,
                            total_requests=int(row["total_requests"] or 0),
                            unique_pages=int(len(pages)),
                            earliest_timesmtamp=row["earliest_timesmtamp"],
                            latest_timesmtamp=row["latest_timesmtamp"],
                        )
                    )
                else:
                    existing.ip_location_json = ip_location_json
                    existing.city = city
                    existing.country_name = country_name
                    existing.continent_name = continent_name
                    existing.pages_json = pages
                    existing.total_requests = int(row["total_requests"] or 0)
                    existing.unique_pages = int(len(pages))
                    existing.earliest_timesmtamp = row["earliest_timesmtamp"]
                    existing.latest_timesmtamp = row["latest_timesmtamp"]
                    to_update.append(existing)

                created_or_updated += 1

                if print_each:
                    self.stdout.write(
                        f"  - Done: queued | earliest={row['earliest_timesmtamp']} | latest={row['latest_timesmtamp']}"
                    )
                elif idx % progress_every == 0 or idx == total_ips:
                    self.stdout.write(
                        f"Progress: {idx}/{total_ips} IPs summarized..."
                    )

            self.stdout.write("Finalizing: writing RequestPageSummary rows (bulk)...")
            t_write = time.time()
            if to_create:
                RequestPageSummary.objects.bulk_create(to_create, batch_size=500)
            if to_update:
                RequestPageSummary.objects.bulk_update(
                    to_update,
                    fields=[
                        "ip_location_json",
                        "city",
                        "country_name",
                        "continent_name",
                        "pages_json",
                        "total_requests",
                        "unique_pages",
                        "earliest_timesmtamp",
                        "latest_timesmtamp",
                        "updated_at",
                    ],
                    batch_size=500,
                )
            self.stdout.write(f"Finalizing: summaries written in {time.time() - t_write:.2f}s")

            self.stdout.write("Finalizing: deleting RequestPage rows (bulk)...")
            t_del = time.time()

            # Deleting RequestPage can be slow if the M2M table (RequestLog.requestPages) is large.
            # Clearing the through table first is typically much faster.
            through_model = RequestLog.requestPages.through
            through_deleted, _ = through_model.objects.all().delete()
            self.stdout.write(f"Finalizing: cleared M2M rows={through_deleted}")

            deleted_count, _ = RequestPage.objects.all().delete()
            deleted_request_pages = int(deleted_count)
            self.stdout.write(f"Finalizing: RequestPage deleted in {time.time() - t_del:.2f}s")

        remaining = RequestPage.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Summarized {created_or_updated} IPs into RequestPageSummary"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Deleted {deleted_request_pages} RequestPage rows"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Remaining RequestPage rows now: {remaining}"
            )
        )
        self.stdout.write(self.style.SUCCESS(f"Total runtime: {time.time() - t0:.2f}s"))
        self.stdout.write(self.style.SUCCESS("=== Done ===\n"))
