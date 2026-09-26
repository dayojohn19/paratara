from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core import mail
from django.test import override_settings
from datetime import timedelta

from unittest.mock import patch

from resorts.models import Packages, resortItem, resortPackages
from .models import CheckinDay, Checkins, ResortBookingPayment


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
        self.assertEqual(Checkins.objects.count(), 1)
        self.assertEqual(CheckinDay.objects.filter(checkin=self.room).count(), 3)
        payment.refresh_from_db()
        self.assertIsNotNone(payment.receipt_email_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['guest@example.com'])
        self.assertEqual(mail.outbox[0].attachments[0][0], 'booking-receipt-qr.png')
        self.assertEqual(mail.outbox[0].attachments[0][2], 'image/png')

        duplicate_response = self.client.get(
            reverse('resort_management:paymongo_booking_return', args=[payment.pk]),
        )

        self.assertEqual(duplicate_response.status_code, 302)
        self.assertIn('/resortManagement/qr/', duplicate_response['Location'])
        self.assertEqual(Checkins.objects.count(), 1)
        self.assertEqual(CheckinDay.objects.filter(checkin=self.room).count(), 3)
        self.assertEqual(len(mail.outbox), 1)
        mocked_retrieve.assert_called_once_with('cs_paid_room')
