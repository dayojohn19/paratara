import base64
import json

from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from django.core import mail
from django.contrib.auth.models import AnonymousUser
from django.test import override_settings
from datetime import datetime, timedelta

from unittest.mock import patch

from resorts.models import Packages, resortItem, resortPackages
from subscription.models import PaymentButton, SourceWebsite, SubscriptionPlan, SubscriptionProduct
from .models import CheckinDay, Checkins, ResortBookingPayment
from .qrcodereceipt import my_page
from .views import _booking_receipt_code, _send_booking_receipt_email


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='bookings@example.com',
)
class PayMongoRoomBookingTests(TestCase):
    def setUp(self):
        self.resort = resortItem.objects.create(
            name='Test Resort',
            RealName='Test Resort',
            latitude=0,
            longitude=0,
            resortQRLink='https://example.com/qr.png',
        )
        self.group = resortPackages.objects.create(PackageTitle='Rooms', ItemOfResort=self.resort)
        self.room = Packages(packageName=self.group, title='Ocean Room', price=1000)
        self.room._skip_event_creation = True
        self.room.save()
        self.form_data = {
            'room': str(self.room.pk),
            'resort': str(self.resort.pk),
            'guest_name': 'Test Guest',
            'guest_email': 'guest@example.com',
            'guest_phone': '09170000000',
            'special_requests': '',
            'checkin_date': '2026-10-10T15:00',
            'checkout_date': '2026-10-12T12:00',
            'totalcost': '1.00',
        }

    def test_booking_receipt_code_includes_establishment_details(self):
        self.resort.address = '12 Shore Road'
        self.resort.contactNumber = '+63 912 345 6789'
        self.resort.contactEmail = 'stay@example.com'
        self.resort.whatsappNumber = '+63 912 345 6789'
        self.resort.open_hours = 'Daily, 8 AM to 8 PM'
        self.resort.websiteURL = 'https://example.com'
        self.resort.description = 'Call ahead for late arrivals.'
        self.resort.save()
        booking = Checkins.objects.create(
            room=self.room,
            resort=self.resort,
            checkin_date=timezone.now(),
            checkout_date=timezone.now() + timedelta(days=1),
            guest_name='Test Guest',
            guest_email='guest@example.com',
            guest_phone='09170000000',
        )

        encoded_booking = _booking_receipt_code(booking)
        receipt_data = json.loads(base64.urlsafe_b64decode(encoded_booking.encode()).decode())

        self.assertEqual(receipt_data['resort_contact_number'], '+63 912 345 6789')
        self.assertEqual(receipt_data['resort_contact_email'], 'stay@example.com')
        self.assertEqual(receipt_data['resort_whatsapp_number'], '+63 912 345 6789')
        self.assertEqual(receipt_data['resort_open_hours'], 'Daily, 8 AM to 8 PM')
        self.assertEqual(receipt_data['resort_website'], 'https://example.com')
        self.assertEqual(receipt_data['resort_description'], 'Call ahead for late arrivals.')

        for field in (
            'resort_contact_number',
            'resort_contact_email',
            'resort_whatsapp_number',
            'resort_open_hours',
            'resort_website',
            'resort_description',
        ):
            receipt_data.pop(field)
        legacy_code = base64.urlsafe_b64encode(json.dumps(receipt_data).encode()).decode()
        request = RequestFactory().get('/resortManagement/qr/')
        request.user = AnonymousUser()
        request.session = {}
        request._messages = []
        response = my_page(request, legacy_code)

        self.assertContains(response, 'Establishment Details')
        self.assertContains(response, 'stay@example.com')
        self.assertContains(response, 'Call ahead for late arrivals.')
        self.assertNotContains(response, 'Please present this QR ticket')

    def test_booking_receipt_email_includes_establishment_details(self):
        self.resort.address = '12 Shore Road'
        self.resort.contactNumber = '+63 912 345 6789'
        self.resort.contactEmail = 'stay@example.com'
        self.resort.whatsappNumber = '+63 912 345 6789'
        self.resort.open_hours = 'Daily, 8 AM to 8 PM'
        self.resort.websiteURL = 'https://example.com'
        self.resort.save()
        booking = Checkins.objects.create(
            room=self.room,
            resort=self.resort,
            checkin_date=timezone.now(),
            checkout_date=timezone.now() + timedelta(days=1),
            guest_name='Test Guest',
            guest_email='guest@example.com',
            guest_phone='09170000000',
        )
        payment = ResortBookingPayment.objects.create(
            amount_centavos=105300,
            status='paid',
            booking_data={},
            checkin=booking,
        )
        request = RequestFactory().get('/')

        self.assertTrue(_send_booking_receipt_email(payment, booking, request))

        message = mail.outbox[-1]
        self.assertIn('Address: 12 Shore Road', message.body)
        self.assertIn('Phone: +63 912 345 6789', message.body)
        self.assertIn('Email: stay@example.com', message.body)
        self.assertIn('WhatsApp: +63 912 345 6789', message.body)
        self.assertIn('Website: https://example.com', message.body)
        html_body = message.alternatives[0][0]
        self.assertIn('Daily, 8 AM to 8 PM', html_body)
        self.assertIn('href="http://testserver/est/resort/%s/"' % self.resort.pk, html_body)

    @patch('resortManagement.views.PayMongoClient.create_checkout_session')
    def test_checkout_uses_server_calculated_room_total(self, mocked_checkout):
        mocked_checkout.return_value = (
            {},
            {'data': {'id': 'cs_room_test', 'attributes': {'checkout_url': 'https://checkout.paymongo.com/room-test'}}},
        )

        response = self.client.post(
            reverse('resort_management:paymongo_room_booking_start'),
            data=self.form_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['checkout_url'], 'https://checkout.paymongo.com/room-test')
        transaction = mocked_checkout.call_args.kwargs['transaction']
        self.assertEqual(transaction.amount_centavos, 210600)
        self.assertEqual(ResortBookingPayment.objects.get().amount_centavos, 210600)
        self.assertFalse(Checkins.objects.exists())

    @patch('resortManagement.views.PayMongoClient.create_checkout_session')
    def test_checkout_return_url_uses_current_public_https_host(self, mocked_checkout):
        mocked_checkout.return_value = (
            {},
            {'data': {'id': 'cs_public_return', 'attributes': {'checkout_url': 'https://checkout.paymongo.com/public-return'}}},
        )

        with self.settings(
            ALLOWED_HOSTS=['testserver', 'bookings.example.com'],
            USE_X_FORWARDED_HOST=True,
            SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
        ):
            response = self.client.post(
                reverse('resort_management:paymongo_room_booking_start'),
                data=self.form_data,
                HTTP_X_FORWARDED_HOST='bookings.example.com',
                HTTP_X_FORWARDED_PROTO='https',
            )

        self.assertEqual(response.status_code, 200)
        success_url = mocked_checkout.call_args.kwargs['success_url']
        self.assertTrue(success_url.startswith('https://bookings.example.com/'))
        self.assertNotIn('127.0.0.1', success_url)

    @patch('resortManagement.views.PayMongoClient.create_checkout_session')
    def test_stale_pending_hold_expires_and_allows_new_checkout(self, mocked_checkout):
        mocked_checkout.return_value = (
            {},
            {'data': {'id': 'cs_new_after_expiry', 'attributes': {'checkout_url': 'https://checkout.paymongo.com/new'}}},
        )
        expired_payment = ResortBookingPayment.objects.create(
            checkout_session_id='cs_old_pending',
            amount_centavos=210600,
            booking_data={
                'room': self.room.pk,
                'resort': self.resort.pk,
                'guest_name': 'Old Guest',
                'guest_email': 'old@example.com',
                'guest_phone': '09170000000',
                'special_requests': '',
                'checkin_date': '2026-10-10T15:00:00+00:00',
                'checkout_date': '2026-10-12T12:00:00+00:00',
            },
        )
        ResortBookingPayment.objects.filter(pk=expired_payment.pk).update(
            created_at=timezone.now() - timedelta(minutes=31),
        )

        response = self.client.post(
            reverse('resort_management:paymongo_room_booking_start'),
            data=self.form_data,
        )

        self.assertEqual(response.status_code, 200)
        expired_payment.refresh_from_db()
        self.assertEqual(expired_payment.status, 'expired')
        self.assertEqual(ResortBookingPayment.objects.count(), 2)
        mocked_checkout.assert_called_once()

    @patch('resortManagement.views.PayMongoClient.retrieve_checkout_session')
    @patch('resortManagement.views.PayMongoClient.create_checkout_session')
    def test_retry_resumes_matching_pending_checkout(self, mocked_create, mocked_retrieve):
        checkout_url = 'https://checkout.paymongo.com/room-resume'
        mocked_create.return_value = (
            {},
            {'data': {'id': 'cs_room_resume', 'attributes': {'checkout_url': checkout_url}}},
        )
        initial_response = self.client.post(
            reverse('resort_management:paymongo_room_booking_start'),
            data=self.form_data,
        )
        self.assertEqual(initial_response.status_code, 200)

        mocked_create.reset_mock()
        mocked_retrieve.return_value = {
            'data': {
                'id': 'cs_room_resume',
                'attributes': {'status': 'active', 'checkout_url': checkout_url},
            },
        }
        retry_response = self.client.post(
            reverse('resort_management:paymongo_room_booking_start'),
            data=self.form_data,
        )

        self.assertEqual(retry_response.status_code, 200)
        self.assertTrue(retry_response.json()['resumed'])
        self.assertEqual(retry_response.json()['checkout_url'], checkout_url)
        mocked_retrieve.assert_called_once_with('cs_room_resume')
        mocked_create.assert_not_called()
        self.assertEqual(ResortBookingPayment.objects.count(), 1)

    @patch('resortManagement.views.PayMongoClient.retrieve_checkout_session')
    def test_unpaid_checkout_return_does_not_create_booking(self, mocked_retrieve):
        payment = ResortBookingPayment.objects.create(
            checkout_session_id='cs_not_paid',
            amount_centavos=210600,
            booking_data={
                'room': self.room.pk,
                'resort': self.resort.pk,
                'guest_name': 'Test Guest',
                'guest_email': 'guest@example.com',
                'guest_phone': '09170000000',
                'special_requests': '',
                'checkin_date': '2026-10-10T15:00:00',
                'checkout_date': '2026-10-12T12:00:00',
            },
        )
        mocked_retrieve.return_value = {
            'data': {
                'id': 'cs_not_paid',
                'attributes': {'status': 'unpaid', 'payments': []},
            },
        }

        response = self.client.get(
            reverse('resort_management:paymongo_booking_return', args=[payment.pk]),
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Checkins.objects.exists())
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'pending')

    @patch('resortManagement.views.PayMongoClient.retrieve_checkout_session')
    def test_paid_checkout_return_creates_booking(self, mocked_retrieve):
        source = SourceWebsite.objects.create(
            name='Room Booking Source',
            slug='room-booking-source',
        )
        product = SubscriptionProduct.objects.create(name='Ocean Room Booking')
        plan = SubscriptionPlan.objects.create(
            name='October Stay',
            slug='october-stay',
            price='2106.00',
            currency='PHP',
            billingInterval='one_time',
            type='one_time',
            subscriptionProduct=product,
        )
        matching_button = PaymentButton.objects.create(
            source_website=source,
            product=product,
            plan=plan,
            metadata={
                'resort_id': str(self.resort.pk),
                'room_id': str(self.room.pk),
                'checkin_date': '2026-10-10T15:00:00',
                'checkout_date': '2026-10-12T12:00:00',
            },
        )
        other_dates_button = PaymentButton.objects.create(
            source_website=source,
            product=product,
            plan=plan,
            metadata={
                'resort_id': str(self.resort.pk),
                'room_id': str(self.room.pk),
                'checkin_date': '2026-10-11T15:00:00',
                'checkout_date': '2026-10-12T12:00:00',
            },
        )
        payment = ResortBookingPayment.objects.create(
            checkout_session_id='cs_paid_room',
            amount_centavos=210600,
            booking_data={
                'room': self.room.pk,
                'resort': self.resort.pk,
                'guest_name': 'Test Guest',
                'guest_email': 'guest@example.com',
                'guest_phone': '09170000000',
                'special_requests': '',
                'checkin_date': '2026-10-10T15:00:00',
                'checkout_date': '2026-10-12T12:00:00',
            },
        )
        mocked_retrieve.return_value = {
            'data': {
                'id': 'cs_paid_room',
                'attributes': {
                    'status': 'active',
                    'payments': [{
                        'id': 'pay_paid_room',
                        'type': 'payment',
                        'attributes': {'status': 'paid', 'amount': 210600, 'currency': 'PHP'},
                    }],
                },
            },
        }

        response = self.client.get(
            reverse('resort_management:paymongo_booking_return', args=[payment.pk]),
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/resortManagement/qr/', response['Location'])
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'paid')
        self.assertIsNotNone(payment.checkin_id)
        matching_button.refresh_from_db()
        other_dates_button.refresh_from_db()
        self.assertTrue(matching_button.paid)
        self.assertFalse(other_dates_button.paid)
        self.assertEqual(Checkins.objects.count(), 1)
        self.assertEqual(CheckinDay.objects.filter(checkin=self.room).count(), 3)
        payment.refresh_from_db()
        self.assertIsNotNone(payment.receipt_email_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['guest@example.com'])
        qr_attachment = mail.outbox[0].attachments[0]
        self.assertEqual(qr_attachment.get_filename(), 'booking-receipt-qr.png')
        self.assertEqual(qr_attachment.get_content_type(), 'image/png')
        self.assertEqual(qr_attachment['Content-ID'], '<booking-receipt-qr>')

        duplicate_response = self.client.get(
            reverse('resort_management:paymongo_booking_return', args=[payment.pk]),
        )

        self.assertEqual(duplicate_response.status_code, 302)
        self.assertIn('/resortManagement/qr/', duplicate_response['Location'])
        self.assertEqual(Checkins.objects.count(), 1)
        self.assertEqual(CheckinDay.objects.filter(checkin=self.room).count(), 3)
        self.assertEqual(len(mail.outbox), 1)
        mocked_retrieve.assert_called_once_with('cs_paid_room')

    def test_concurrent_receipt_attempt_is_claimed_before_sending(self):
        booking = Checkins.objects.create(
            room=self.room,
            resort=self.resort,
            checkin_date=timezone.make_aware(datetime(2026, 10, 10, 15)),
            checkout_date=timezone.make_aware(datetime(2026, 10, 12, 12)),
            guest_name='Test Guest',
            guest_email='guest@example.com',
            guest_phone='09170000000',
        )
        payment = ResortBookingPayment.objects.create(
            amount_centavos=210600,
            status='paid',
            booking_data={},
            checkin=booking,
        )
        request = RequestFactory().get('/')
        duplicate_attempts = []

        def send_and_retry(*args, **kwargs):
            duplicate_attempts.append(
                _send_booking_receipt_email(payment, booking, request)
            )
            return 1

        with patch('resortManagement.views.EmailMultiAlternatives.send', side_effect=send_and_retry) as send:
            self.assertTrue(_send_booking_receipt_email(payment, booking, request))

        self.assertEqual(send.call_count, 1)
        self.assertEqual(duplicate_attempts, [False])
        payment.refresh_from_db()
        self.assertIsNotNone(payment.receipt_email_sent_at)
