from collections import defaultdict
import time

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Max, Min, Q
from django.contrib.gis.geoip2 import GeoIP2
import os

from home.models import RequestPage, RequestPageSummary


class Command(BaseCommand):
    help = (
        "Summarize RequestPage rows by requesting_ip into RequestPageSummary, "
        "while preserving the original RequestPage rows."
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
        parser.add_argument(
            "--backfill-locations",
            action="store_true",
            help=(
                "Populate missing GeoIP data on existing RequestPageSummary rows. "
                "Useful after RequestPage rows have already been summarized/deleted."
            ),
        )
        parser.add_argument(
            "--force-location-refresh",
            action="store_true",
            help="Refresh GeoIP data even when RequestPageSummary already has location JSON.",
        )

    @staticmethod
    def _clean(value):
        if isinstance(value, str):
            value = value.strip()
        return value or None

    @classmethod
    def _extract_location_names(cls, ip_location_json):
        if not isinstance(ip_location_json, dict):
            return None, None, None

        city_info = ip_location_json.get("city_info") or {}
        country_info = ip_location_json.get("country_info") or {}
        if not isinstance(city_info, dict):
            city_info = {}
        if not isinstance(country_info, dict):
            country_info = {}

        city = cls._clean(city_info.get("city"))
        country_name = cls._clean(
            city_info.get("country_name") or country_info.get("country_name")
        )
        continent_name = cls._clean(
            city_info.get("continent_name") or country_info.get("continent_name")
        )
        return city, country_name, continent_name

    @classmethod
    def _has_usable_location(cls, ip_location_json, city, country_name, continent_name):
        city = cls._clean(city)
        country_name = cls._clean(country_name)
        continent_name = cls._clean(continent_name)
        json_city, json_country_name, json_continent_name = cls._extract_location_names(
            ip_location_json
        )
        return any(
            [
                city,
                country_name,
                continent_name,
                json_city,
                json_country_name,
                json_continent_name,
            ]
        )

    @staticmethod
    def _get_geoip(skip_geoip):
        if skip_geoip:
            return None, "GeoIP2 lookup skipped (--skip-geoip)."

        geoip_path = getattr(settings, "GEOIP_PATH", None)
        if not geoip_path or not os.path.exists(geoip_path):
            return None, "GeoIP2 lookup disabled (GEOIP_PATH missing/invalid)."

        try:
            return GeoIP2(path=geoip_path), None
        except Exception as e:
            return None, f"GeoIP2 lookup disabled ({e})."

    @staticmethod
    def _unavailable_location_json(geo_disabled_reason, skip_geoip):
        return {
            "lookup_status": "skipped" if skip_geoip else "unavailable",
            "error": geo_disabled_reason or "GeoIP2 lookup unavailable.",
        }

    def _lookup_ip_location(self, geo, ip):
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
            city, country_name, continent_name = self._extract_location_names(
                ip_location_json
            )
            return ip_location_json, city, country_name, continent_name
        except Exception as e:
            return {"error": str(e)}, None, None, None

    def _print_geoip_status(self, geo, geo_disabled_reason, skip_geoip):
        if skip_geoip:
            self.stdout.write(self.style.WARNING(geo_disabled_reason))
        elif geo is None:
            self.stdout.write(self.style.WARNING(geo_disabled_reason))
        else:
            self.stdout.write(self.style.SUCCESS("GeoIP2 lookup enabled."))

    def _backfill_summary_locations(
        self,
        *,
        geo,
        geo_disabled_reason,
        dry_run,
        print_each,
        progress_every,
        force_location_refresh,
    ):
        if geo is None:
            self.stdout.write(
                self.style.WARNING(
                    f"Location backfill skipped: {geo_disabled_reason}"
                )
            )
            return 0

        qs = RequestPageSummary.objects.all().only(
            "id",
            "requesting_ip",
            "ip_location_json",
            "city",
            "country_name",
            "continent_name",
        )
        if not force_location_refresh:
            qs = qs.filter(
                Q(ip_location_json__isnull=True)
                | Q(city__isnull=True)
                | Q(city="")
                | Q(country_name__isnull=True)
                | Q(country_name="")
                | Q(continent_name__isnull=True)
                | Q(continent_name="")
            )

        total = qs.count()
        if total == 0:
            self.stdout.write("Location backfill: no candidate summaries found.")
            return 0

        self.stdout.write(
            f"Location backfill: checking {total} RequestPageSummary rows..."
        )

        to_update = []
        changed = 0
        checked = 0

        for summary in qs.iterator(chunk_size=500):
            checked += 1
            original = (
                summary.ip_location_json,
                summary.city,
                summary.country_name,
                summary.continent_name,
            )

            ip_location_json = summary.ip_location_json
            city = self._clean(summary.city)
            country_name = self._clean(summary.country_name)
            continent_name = self._clean(summary.continent_name)

            json_city, json_country_name, json_continent_name = (
                self._extract_location_names(ip_location_json)
            )
            city = city or json_city
            country_name = country_name or json_country_name
            continent_name = continent_name or json_continent_name

            should_lookup = force_location_refresh or not self._has_usable_location(
                ip_location_json,
                city,
                country_name,
                continent_name,
            )
            if should_lookup:
                ip_location_json, city, country_name, continent_name = (
                    self._lookup_ip_location(geo, summary.requesting_ip)
                )

            updated = (
                ip_location_json,
                city,
                country_name,
                continent_name,
            )
            if updated != original:
                summary.ip_location_json = ip_location_json
                summary.city = city
                summary.country_name = country_name
                summary.continent_name = continent_name
                to_update.append(summary)
                changed += 1

                if print_each:
                    self.stdout.write(
                        f"  - {summary.requesting_ip}: "
                        f"continent={continent_name or 'N/A'} "
                        f"country={country_name or 'N/A'} "
                        f"city={city or 'N/A'}"
                    )

            if len(to_update) >= 500:
                if not dry_run:
                    RequestPageSummary.objects.bulk_update(
                        to_update,
                        fields=[
                            "ip_location_json",
                            "city",
                            "country_name",
                            "continent_name",
                            "updated_at",
                        ],
                        batch_size=500,
                    )
                to_update.clear()

            if not print_each and (
                checked % progress_every == 0 or checked == total
            ):
                self.stdout.write(
                    f"Location backfill progress: {checked}/{total} checked..."
                )

        if to_update and not dry_run:
            RequestPageSummary.objects.bulk_update(
                to_update,
                fields=[
                    "ip_location_json",
                    "city",
                    "country_name",
                    "continent_name",
                    "updated_at",
                ],
                batch_size=500,
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: {changed} RequestPageSummary rows would be updated."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Location backfill complete: updated {changed} RequestPageSummary rows."
                )
            )
        return changed

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        print_each = options.get("print_each", False)
        progress_every = int(options.get("progress_every") or 100)
        skip_geoip = options.get("skip_geoip", False)
        backfill_locations = options.get("backfill_locations", False)
        force_location_refresh = options.get("force_location_refresh", False)
        if progress_every < 1:
            progress_every = 1

        geo, geo_disabled_reason = self._get_geoip(skip_geoip)

        total_request_pages = RequestPage.objects.count()
        t0 = time.time()

        self.stdout.write("\n=== RequestPage Summarizer ===")
        self._print_geoip_status(geo, geo_disabled_reason, skip_geoip)

        if backfill_locations:
            self._backfill_summary_locations(
                geo=geo,
                geo_disabled_reason=geo_disabled_reason,
                dry_run=dry_run,
                print_each=print_each,
                progress_every=progress_every,
                force_location_refresh=force_location_refresh,
            )

        if total_request_pages == 0:
            self.stdout.write(self.style.WARNING("No RequestPage rows found."))
            return

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
        ips = [row["requesting_ip"] for row in ip_aggs]
        existing_summaries = RequestPageSummary.objects.filter(requesting_ip__in=ips)
        existing_by_ip = {s.requesting_ip: s for s in existing_summaries}

        to_create: list[RequestPageSummary] = []
        to_update: list[RequestPageSummary] = []

        t3 = time.time()
        with transaction.atomic():
            total_ips = len(ip_aggs)
            self.stdout.write("Phase 3/3: writing summaries and preserving RequestPage rows...")
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

                    json_city, json_country_name, json_continent_name = (
                        self._extract_location_names(ip_location_json)
                    )
                    city = city or json_city
                    country_name = country_name or json_country_name
                    continent_name = continent_name or json_continent_name

                need_geo = (
                    geo is not None
                    and (
                        force_location_refresh
                        or existing is None
                        or not self._has_usable_location(
                            ip_location_json,
                            city,
                            country_name,
                            continent_name,
                        )
                    )
                )

                if need_geo:
                    if print_each:
                        self.stdout.write(f"  - GeoIP: looking up city/country...")
                    ip_location_json, city, country_name, continent_name = (
                        self._lookup_ip_location(geo, ip)
                    )
                    if print_each:
                        city_data = (
                            ip_location_json.get("city_info")
                            if isinstance(ip_location_json, dict)
                            else {}
                        )
                        country_data = (
                            ip_location_json.get("country_info")
                            if isinstance(ip_location_json, dict)
                            else {}
                        )
                        if isinstance(city_data, dict) and "error" in city_data:
                            self.stdout.write(
                                f"  - GeoIP(city) error: {city_data.get('error')}"
                            )
                        if isinstance(country_data, dict) and "error" in country_data:
                            self.stdout.write(
                                f"  - GeoIP(country) error: {country_data.get('error')}"
                            )
                        self.stdout.write(
                            f"  - GeoIP: continent={continent_name or 'N/A'} country={country_name or 'N/A'} city={city or 'N/A'}"
                        )
                elif print_each:
                    if skip_geoip:
                        self.stdout.write("  - GeoIP: skipped (--skip-geoip)")
                    elif geo is None:
                        self.stdout.write("  - GeoIP: skipped (GEOIP_PATH missing/invalid)")
                    else:
                        self.stdout.write("  - GeoIP: skipped (already has location)")

                if ip_location_json is None and geo is None:
                    ip_location_json = self._unavailable_location_json(
                        geo_disabled_reason,
                        skip_geoip,
                    )

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

            self.stdout.write("Finalizing: preserving RequestPage rows for raw visit analytics.")

        remaining = RequestPage.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Summarized {created_or_updated} IPs into RequestPageSummary"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "✓ Deleted 0 RequestPage rows"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Remaining RequestPage rows now: {remaining}"
            )
        )
        self.stdout.write(self.style.SUCCESS(f"Total runtime: {time.time() - t0:.2f}s"))
        self.stdout.write(self.style.SUCCESS("=== Done ===\n"))
