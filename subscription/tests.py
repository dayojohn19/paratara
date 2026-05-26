import requests
import hashlib
import hmac
import json
import time
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from userProfile.models import UserCredentialsBackUP, userPoster

from .models import (
    PaymentButton,
    PayMongoWebhookEvent,
    SourceWebsite,
    Subscription,
    SubscriptionPlan,
    SubscriptionProduct,
    Transaction,
)
from .services.paymongo import amount_to_centavos, make_embed_token, verify_embed_token
from .webhooks import _fetch_paypal_subscription_details, _get_or_create_paypal_user


class PayPalWebhookUserTests(TestCase):
    @patch("subscription.webhooks._send_paypal_password_reset_email", return_value=True)
    def test_get_or_create_paypal_user_creates_auth_user_and_profile(self, mocked_send_reset):
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
        self.assertEqual(user.username, "subscriber@example.com")
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
        mocked_send_reset.assert_called_once_with(user, request=None)

    @patch("subscription.webhooks._send_paypal_password_reset_email", return_value=True)
    def test_get_or_create_paypal_user_does_not_send_reset_email_for_existing_user(self, mocked_send_reset):
        User = get_user_model()
        User.objects.create_user(
            username="existing",
            email="subscriber@example.com",
            password="secret-pass",
        )

        _get_or_create_paypal_user(
            email="subscriber@example.com",
            full_name="Existing Subscriber",
            subscriber_name={"given_name": "Existing", "surname": "Subscriber"},
            payer_id="PAYER123",
            subscription_id="SUB123",
        )
        mocked_send_reset.assert_not_called()

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


class PayMongoModelAndServiceTests(TestCase):
    def setUp(self):
        self.source = SourceWebsite.objects.create(
            name="Standalone Site",
            slug="standalone-site",
            allowed_origins=["https://standalone.example"],
        )
        self.product = SubscriptionProduct.objects.create(
            name="Booking SaaS",
            description="Subscription manager",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly Pro",
            slug="monthly-pro",
            price=Decimal("499.00"),
            currency="PHP",
            billingInterval="monthly",
            type="subscription",
            status="active",
            subscriptionProduct=self.product,
        )
        self.button = PaymentButton.objects.create(
            source_website=self.source,
            product=self.product,
            plan=self.plan,
            label="Subscribe Now",
        )

    def test_amount_to_centavos(self):
        self.assertEqual(amount_to_centavos("499.00"), 49900)
        self.assertEqual(amount_to_centavos(Decimal("10.55")), 1055)

    def test_embed_token_round_trip(self):
        token = make_embed_token(self.button)
        payload = verify_embed_token(token, self.button)

        self.assertEqual(payload["button_public_id"], self.button.public_id)
        self.assertEqual(payload["source_public_id"], self.source.public_id)

    def test_public_ids_are_not_database_ids(self):
        self.assertTrue(self.source.public_id.startswith("src_"))
        self.assertTrue(self.button.public_id.startswith("btn_"))
        self.assertNotEqual(self.button.public_id, str(self.button.pk))


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PAYMONGO_SECRET_KEY="sk_test_x",
    PAYMONGO_WEBHOOK_SECRET="whsec_test",
    PAYMONGO_MODE="test",
    PAYMONGO_ALLOWED_PAYMENT_METHODS=["card", "gcash"],
    DJANGO_PAYMENT_BASE_URL="https://www.paratara.com",
)
class PayMongoCheckoutAndWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.source = SourceWebsite.objects.create(
            name="Standalone Site",
            slug="standalone-site",
            allowed_origins=["https://standalone.example"],
        )
        self.product = SubscriptionProduct.objects.create(name="Booking SaaS")
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly Pro",
            slug="monthly-pro",
            price=Decimal("499.00"),
            currency="PHP",
            billingInterval="monthly",
            type="subscription",
            status="active",
            subscriptionProduct=self.product,
        )
        self.button = PaymentButton.objects.create(
            source_website=self.source,
            product=self.product,
            plan=self.plan,
            label="Subscribe Now",
        )

    @patch("subscription.views.PayMongoClient.create_checkout_session")
    def test_checkout_uses_server_side_amount_and_creates_transaction(self, mocked_checkout):
        mocked_checkout.return_value = (
            {"data": {"attributes": {"metadata": {"example": "payload"}}}},
            {
                "data": {
                    "id": "cs_test_123",
                    "attributes": {"checkout_url": "https://checkout.paymongo.com/test"},
                }
            },
        )
        token = make_embed_token(self.button)

        response = self.client.post(
            reverse("subscription:paymongo_start_checkout", args=[self.button.public_id]),
            data={
                "embed_token": token,
                "customer_email": "customer@example.com",
                "amount": "1.00",
            },
            HTTP_ORIGIN="https://standalone.example",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://checkout.paymongo.com/test")

        transaction = Transaction.objects.get()
        self.assertEqual(transaction.amount, Decimal("499.00"))
        self.assertEqual(transaction.amount_centavos, 49900)
        self.assertEqual(transaction.status, "checkout_created")
        self.assertEqual(transaction.customer_email, "customer@example.com")
        self.assertEqual(transaction.paymongo_checkout_session_id, "cs_test_123")

    def _signed_webhook(self, payload):
        raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        timestamp = str(int(time.time()))
        signature = hmac.new(
            b"whsec_test",
            timestamp.encode("utf-8") + b"." + raw_body,
            hashlib.sha256,
        ).hexdigest()
        return raw_body, f"t={timestamp},te={signature}"

    def test_paid_webhook_is_idempotent_and_activates_subscription(self):
        transaction = Transaction.objects.create(
            source_website=self.source,
            product=self.product,
            plan=self.plan,
            payment_button=self.button,
            customer_email="customer@example.com",
            amount=self.plan.price,
            amount_centavos=49900,
            currency="PHP",
            paymongo_checkout_session_id="cs_test_123",
        )
        payload = {
            "data": {
                "id": "evt_test_123",
                "attributes": {
                    "type": "checkout_session.payment.paid",
                    "data": {
                        "id": "cs_test_123",
                        "type": "checkout_session",
                        "attributes": {
                            "status": "paid",
                            "metadata": {
                                "internal_reference_id": transaction.internal_reference_id,
                                "source_website": self.source.slug,
                                "product_id": str(self.product.pk),
                                "plan_id": str(self.plan.pk),
                                "customer_email": "customer@example.com",
                            },
                            "payments": [{"id": "pay_test_123"}],
                        },
                    },
                },
            }
        }
        raw_body, signature_header = self._signed_webhook(payload)
        webhook_url = reverse("subscription:paymongo_webhook")

        response = self.client.post(
            webhook_url,
            data=raw_body,
            content_type="application/json",
            HTTP_PAYMONGO_SIGNATURE=signature_header,
        )
        self.assertEqual(response.status_code, 200)

        transaction.refresh_from_db()
        self.assertEqual(transaction.status, "paid")
        self.assertEqual(transaction.paymongo_payment_id, "pay_test_123")
        self.assertIsNotNone(transaction.paid_at)

        subscription = Subscription.objects.get()
        self.assertEqual(subscription.status, "active")
        self.assertEqual(subscription.transaction_id, transaction.id)
        self.assertIsNotNone(subscription.current_period_end)

        duplicate = self.client.post(
            webhook_url,
            data=raw_body,
            content_type="application/json",
            HTTP_PAYMONGO_SIGNATURE=signature_header,
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertTrue(duplicate.json()["duplicate"])
        self.assertEqual(PayMongoWebhookEvent.objects.filter(paymongo_event_id="evt_test_123").count(), 1)

    def test_webhook_rejects_invalid_signature(self):
        payload = {"data": {"id": "evt_bad", "attributes": {"type": "payment.paid"}}}

        response = self.client.post(
            reverse("subscription:paymongo_webhook"),
            data=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            HTTP_PAYMONGO_SIGNATURE="t=1,te=bad",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PayMongoWebhookEvent.objects.filter(processing_status="invalid").count(), 1)
