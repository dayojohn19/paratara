import requests
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from userProfile.models import UserCredentialsBackUP, userPoster

from .webhooks import _fetch_paypal_subscription_details, _get_or_create_paypal_user


class PayPalWebhookUserTests(TestCase):
    def test_get_or_create_paypal_user_creates_auth_user_and_profile(self):
        user = _get_or_create_paypal_user(
            email="subscriber@example.com",
            full_name="PayPal Subscriber",
            subscriber_name={"given_name": "PayPal", "surname": "Subscriber"},
            payer_id="PAYER123",
            subscription_id="SUB123",
        )

        user.refresh_from_db()
        profile = userPoster.objects.get(userID=user.pk)

        self.assertEqual(user.email, "subscriber@example.com")
        self.assertEqual(user.first_name, "PayPal")
        self.assertEqual(user.last_name, "Subscriber")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.additionalCreds_id, profile.pk)
        self.assertEqual(profile.name, "PayPal Subscriber")
        self.assertEqual(profile.contact, "subscriber@example.com")
        self.assertTrue(
            UserCredentialsBackUP.objects.filter(
                userID=user.pk,
                userPassword="paypal:PAYER123",
            ).exists()
        )

    def test_get_or_create_paypal_user_reuses_existing_email_user(self):
        User = get_user_model()
        existing_user = User.objects.create_user(
            username="existing",
            email="subscriber@example.com",
            password="secret-pass",
        )

        user = _get_or_create_paypal_user(
            email="subscriber@example.com",
            full_name="Existing Subscriber",
            subscriber_name={"given_name": "Existing", "surname": "Subscriber"},
            payer_id="PAYER123",
            subscription_id="SUB123",
        )

        existing_user.refresh_from_db()

        self.assertEqual(user.pk, existing_user.pk)
        self.assertEqual(existing_user.first_name, "Existing")
        self.assertEqual(existing_user.last_name, "Subscriber")
        self.assertEqual(userPoster.objects.filter(userID=existing_user.pk).count(), 1)
        self.assertTrue(UserCredentialsBackUP.objects.filter(userID=existing_user.pk).exists())

    def test_get_or_create_paypal_user_without_email_reuses_paypal_username(self):
        first_user = _get_or_create_paypal_user(
            email=None,
            full_name="PayPal Subscriber",
            subscriber_name={"given_name": "PayPal", "surname": "Subscriber"},
            payer_id="PAYER123",
            subscription_id="SUB123",
        )
        second_user = _get_or_create_paypal_user(
            email=None,
            full_name="PayPal Subscriber",
            subscriber_name={"given_name": "PayPal", "surname": "Subscriber"},
            payer_id="PAYER123",
            subscription_id="SUB123",
        )

        self.assertEqual(second_user.pk, first_user.pk)
        self.assertEqual(first_user.username, "paypal_payer123")
        self.assertEqual(UserCredentialsBackUP.objects.filter(userID=first_user.pk).count(), 1)


class PayPalDetailsFetchTests(TestCase):
    def test_fetch_paypal_subscription_details_retries_transient_error(self):
        failed_response = Mock(status_code=503)
        failed_error = requests.HTTPError("503 Server Error", response=failed_response)
        failed_response.raise_for_status.side_effect = failed_error

        successful_response = Mock(status_code=200)
        successful_response.raise_for_status.return_value = None
        successful_response.json.return_value = {"id": "SUB123"}

        with patch("subscription.webhooks.requests.get", side_effect=[failed_response, successful_response]) as mocked_get:
            with patch("subscription.webhooks.time.sleep") as mocked_sleep:
                details = _fetch_paypal_subscription_details(
                    "SUB123",
                    "access-token",
                    "https://api-m.sandbox.paypal.com",
                )

        self.assertEqual(details, {"id": "SUB123"})
        self.assertEqual(mocked_get.call_count, 2)
        mocked_sleep.assert_called_once_with(1)

    def test_fetch_paypal_subscription_details_does_not_retry_permanent_error(self):
        failed_response = Mock(status_code=401)
        failed_error = requests.HTTPError("401 Client Error", response=failed_response)
        failed_response.raise_for_status.side_effect = failed_error

        with patch("subscription.webhooks.requests.get", return_value=failed_response) as mocked_get:
            with patch("subscription.webhooks.time.sleep") as mocked_sleep:
                with self.assertRaises(requests.HTTPError):
                    _fetch_paypal_subscription_details(
                        "SUB123",
                        "access-token",
                        "https://api-m.sandbox.paypal.com",
                    )

        self.assertEqual(mocked_get.call_count, 1)
        mocked_sleep.assert_not_called()
