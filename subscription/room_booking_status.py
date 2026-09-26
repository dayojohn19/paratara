
from django.utils import timezone
from django.utils.dateparse import parse_datetime


def room_booking_matches_button_metadata(booking_data, metadata):
    if not isinstance(booking_data, dict) or not isinstance(metadata, dict):
        return False

    if str(booking_data.get('resort')) != str(metadata.get('resort_id')):
        return False
    if str(booking_data.get('room')) != str(metadata.get('room_id')):
        return False

    for booking_key, metadata_key in (
        ('checkin_date', 'checkin_date'),
        ('checkout_date', 'checkout_date'),
    ):
        booking_date = parse_datetime(str(booking_data.get(booking_key) or ''))
        metadata_date = parse_datetime(str(metadata.get(metadata_key) or ''))
        if not booking_date or not metadata_date:
            return False
        if timezone.is_naive(booking_date):
            booking_date = timezone.make_aware(booking_date)
        if timezone.is_naive(metadata_date):
            metadata_date = timezone.make_aware(metadata_date)
        if booking_date != metadata_date:
            return False

    return True


def mark_room_booking_button_paid(booking_data):
    from .models import PaymentButton

    buttons = PaymentButton.objects.only('id', 'metadata', 'paid')
    for button in buttons.iterator():
        if room_booking_matches_button_metadata(booking_data, button.metadata) and not button.paid:
            button.paid = True
            button.save(update_fields=['paid', 'updated_at'])