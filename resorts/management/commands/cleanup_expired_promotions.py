from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

from home.models import allSchedules
from resorts.models import Packages

class Command(BaseCommand):
    help = (
        "Delete expired promotion subpackages (and clean up related events/images via signals), "
        "and delete expired allSchedules entries."
    )

    def handle(self, *args, **options):
        now = timezone.now()
        expired_promotions = Packages.objects.filter(expires_at__isnull=False, expires_at__lt=now)
        expired_promotions_total = expired_promotions.count()
        for promotion in expired_promotions:
            title = promotion.title
            try:
                promotion.delete()
                self.stdout.write(self.style.SUCCESS(f"Deleted expired promotion: {title}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to delete {title}: {e}"))

        today = timezone.localdate()
        expired_schedules = allSchedules.objects.filter(
            Q(yearN__lt=today.year)
            | Q(yearN=today.year, monthN__lt=today.month)
            | Q(yearN=today.year, monthN=today.month, dateN__lt=today.day)
        )
        expired_schedules_total = expired_schedules.count()
        for sched in expired_schedules:
            title = sched.scheduleTitle or "(no title)"
            try:
                sched.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Deleted expired schedule: id={sched.id} title={title} date={sched.monthN}/{sched.dateN}/{sched.yearN}"
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to delete schedule id={sched.id} title={title}: {e}"))

        self.stdout.write(
            self.style.WARNING(
                "Cleanup complete. "
                f"Deleted promotions: {expired_promotions_total}. "
                f"Deleted schedules: {expired_schedules_total}."
            )
        )
