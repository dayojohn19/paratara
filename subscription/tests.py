import requests
import hashlib
import hmac
import json
import time
from decimal import Decimal
from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from userProfile.models import UserCredentialsBackUP, userPoster

from .forms import PaymentButtonForm
from .models import (
    Customer,
    PaymentButton,
    PayMongoWebhookEvent,
    SourceWebsite,
    Subscription,
    SubscriptionPlan,
    SubscriptionProduct,
    Transaction,
    UserSubscription,
)
from .services.paymongo import PayMongoClient, amount_to_centavos, make_embed_token, verify_embed_token
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

    def test_weekly_subscription_period_end(self):
        self.plan.billingInterval = "weekly"
        start_at = timezone.now()

        period_end = Subscription.period_end_for_plan(self.plan, start_at)

        self.assertEqual(period_end, start_at + timedelta(days=7))

    def test_payment_link_button_form_extracts_reference_from_url(self):
        form = PaymentButtonForm(
            data={
                "source_website": self.source.pk,
                "product": self.product.pk,
                "plan": self.plan.pk,
                "label": "Pay Link",
                "checkout_mode": "paymongo_link",
                "active": "on",
                "payment_link_url": "https://pm.link/org-LE2YAQrsDm1hi7RJFcdVrj1r/b5vnlvt",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        button = form.save()
        self.assertEqual(button.payment_link_reference, "b5vnlvt")


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PAYMONGO_SECRET_KEY="sk_test_x",
    PAYMONGO_WEBHOOK_SECRET="whsec_test",
    PAYMONGO_MODE="test",
    PAYMONGO_ALLOWED_PAYMENT_METHODS=["card", "gcash"],
    PAYMONGO_FLOW_PRINT_DELAY_SECONDS=0,
    PAYMONGO_CREATE_CUSTOMER_RESOURCE=False,
    PAYMONGO_CUSTOMER_API_VERSION="v2",
    PAYMONGO_ATTACH_CUSTOMER_TO_CHECKOUT=True,
    PAYMONGO_CHECKOUT_CUSTOMER_ID_FALLBACK=True,
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

    @override_settings(PAYMONGO_CREATE_CUSTOMER_RESOURCE=True)
    @patch("subscription.views.PayMongoClient.create_checkout_session")
    @patch("subscription.views.PayMongoClient.create_customer")
    def test_checkout_creates_paymongo_customer_resource(
        self,
        mocked_create_customer,
        mocked_checkout,
    ):
        mocked_create_customer.return_value = {
            "data": {
                "id": "cust_test_123",
                "attributes": {
                    "email": "customer@example.com",
                    "name": "PayMongo Customer",
                    "mobile_phone": "+639171234567",
                },
            }
        }
        mocked_checkout.return_value = (
            {"data": {"attributes": {"metadata": {"example": "payload"}}}},
            {
                "data": {
                    "id": "cs_test_customer",
                    "attributes": {"checkout_url": "https://checkout.paymongo.com/test-customer"},
                }
            },
        )
        token = make_embed_token(self.button)

        response = self.client.post(
            reverse("subscription:paymongo_start_checkout", args=[self.button.public_id]),
            data={
                "embed_token": token,
                "customer_email": "customer@example.com",
                "customer_name": "PayMongo Customer",
                "customer_phone": "09171234567",
            },
            HTTP_ORIGIN="https://standalone.example",
        )

        self.assertEqual(response.status_code, 302)
        mocked_create_customer.assert_called_once_with(
            email="customer@example.com",
            name="PayMongo Customer",
            phone="+639171234567",
        )

        customer = Customer.objects.get(email="customer@example.com")
        self.assertEqual(customer.paymongo_customer_id, "cust_test_123")
        self.assertEqual(customer.metadata["paymongo_customer_sync_source"], "create")

    @patch("subscription.services.paymongo.requests.request")
    def test_checkout_session_payload_links_paymongo_customer_id(self, mocked_request):
        paymongo_response = Mock(status_code=200, ok=True)
        paymongo_response.json.return_value = {
            "data": {
                "id": "cs_customer_link",
                "attributes": {"checkout_url": "https://checkout.paymongo.com/customer-link"},
            }
        }
        mocked_request.return_value = paymongo_response
        customer = Customer.objects.create(
            source_website=self.source,
            email="customer@example.com",
            paymongo_customer_id="cust_test_123",
        )
        payment_transaction = Transaction.objects.create(
            source_website=self.source,
            product=self.product,
            plan=self.plan,
            payment_button=self.button,
            customer=customer,
            customer_email=customer.email,
            amount=self.plan.price,
            amount_centavos=49900,
            currency="PHP",
        )

        payload, _ = PayMongoClient().create_checkout_session(
            transaction=payment_transaction,
            line_item_name=self.plan.name,
            description=self.plan.description,
            success_url="https://www.paratara.com/success",
            cancel_url="https://www.paratara.com/cancel",
            metadata={"internal_reference_id": payment_transaction.internal_reference_id},
        )

        request_payload = mocked_request.call_args.kwargs["json"]
        self.assertEqual(request_payload["data"]["attributes"]["customer_id"], "cust_test_123")
        self.assertEqual(payload["data"]["attributes"]["metadata"]["paymongo_customer_id"], "cust_test_123")

    @patch("subscription.services.paymongo.requests.request")
    def test_checkout_session_retries_without_customer_id_if_paymongo_rejects_it(self, mocked_request):
        rejected_response = Mock(status_code=400, ok=False)
        rejected_response.json.return_value = {"errors": [{"detail": "customer_id is not allowed"}]}
        accepted_response = Mock(status_code=200, ok=True)
        accepted_response.json.return_value = {
            "data": {
                "id": "cs_without_customer_link",
                "attributes": {"checkout_url": "https://checkout.paymongo.com/no-customer-link"},
            }
        }
        mocked_request.side_effect = [rejected_response, accepted_response]
        customer = Customer.objects.create(
            source_website=self.source,
            email="customer@example.com",
            paymongo_customer_id="cust_test_123",
        )
        payment_transaction = Transaction.objects.create(
            source_website=self.source,
            product=self.product,
            plan=self.plan,
            payment_button=self.button,
            customer=customer,
            customer_email=customer.email,
            amount=self.plan.price,
            amount_centavos=49900,
            currency="PHP",
        )

        payload, response = PayMongoClient().create_checkout_session(
            transaction=payment_transaction,
            line_item_name=self.plan.name,
            description=self.plan.description,
            success_url="https://www.paratara.com/success",
            cancel_url="https://www.paratara.com/cancel",
            metadata={"internal_reference_id": payment_transaction.internal_reference_id},
        )

        first_payload = mocked_request.call_args_list[0].kwargs["json"]
        second_payload = mocked_request.call_args_list[1].kwargs["json"]
        self.assertEqual(first_payload["data"]["attributes"]["customer_id"], "cust_test_123")
        self.assertNotIn("customer_id", second_payload["data"]["attributes"])
        self.assertNotIn("customer_id", payload["data"]["attributes"])
        self.assertEqual(response["data"]["id"], "cs_without_customer_link")

    @patch("subscription.views.PayMongoClient.create_checkout_session")
    def test_checkout_posts_to_specific_payment_button_url(self, mocked_checkout):
        specific_button_id = "btn_c0a3733eb3094a7b966ccd58"
        self.button.public_id = specific_button_id
        self.button.checkout_mode = "hosted_checkout"
        self.button.save(update_fields=["public_id", "checkout_mode"])

        mocked_checkout.return_value = (
            {"data": {"attributes": {"metadata": {"example": "payload"}}}},
            {
                "data": {
                    "id": "cs_specific_button",
                    "attributes": {"checkout_url": "https://checkout.paymongo.com/specific-button"},
                }
            },
        )
        token = make_embed_token(self.button)

        response = self.client.post(
            f"/subscription/pay/{specific_button_id}/",
            data={
                "embed_token": token,
                "customer_email": "specific@example.com",
                "customer_name": "Specific Customer",
                "amount": "1.00",
            },
            HTTP_ORIGIN="https://standalone.example",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://checkout.paymongo.com/specific-button")

        transaction = Transaction.objects.get(paymongo_checkout_session_id="cs_specific_button")
        self.assertEqual(transaction.payment_button.public_id, specific_button_id)
        self.assertEqual(transaction.amount, Decimal("499.00"))
        self.assertEqual(transaction.amount_centavos, 49900)
        self.assertEqual(transaction.customer_email, "specific@example.com")
        self.assertEqual(transaction.status, "checkout_created")

    @patch("subscription.views.PayMongoClient.create_checkout_session")
    def test_payment_link_button_redirects_to_existing_paymongo_link(self, mocked_checkout):
        self.button.checkout_mode = "paymongo_link"
        self.button.payment_link_url = "https://pm.link/org-LE2YAQrsDm1hi7RJFcdVrj1r/b5vnlvt"
        self.button.payment_link_reference = "b5vnlvt"
        self.button.save(update_fields=["checkout_mode", "payment_link_url", "payment_link_reference"])
        token = make_embed_token(self.button)

        response = self.client.post(
            reverse("subscription:paymongo_start_checkout", args=[self.button.public_id]),
            data={
                "embed_token": token,
                "customer_email": "link-click@example.com",
            },
            HTTP_ORIGIN="https://standalone.example",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://pm.link/org-LE2YAQrsDm1hi7RJFcdVrj1r/b5vnlvt")
        mocked_checkout.assert_not_called()

        transaction = Transaction.objects.get()
        self.assertEqual(transaction.status, "checkout_created")
        self.assertEqual(transaction.checkout_url, "https://pm.link/org-LE2YAQrsDm1hi7RJFcdVrj1r/b5vnlvt")
        self.assertEqual(transaction.paymongo_reference_number, "b5vnlvt")
        self.assertEqual(transaction.customer_email, "link-click@example.com")

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

        User = get_user_model()
        payment_user = User.objects.get(email="customer@example.com")
        self.assertEqual(payment_user.username, "customer@example.com")
        self.assertFalse(payment_user.has_usable_password())
        self.assertTrue(
            UserCredentialsBackUP.objects.filter(
                userID=payment_user.pk,
                userPassword__startswith="paymongo:",
            ).exists()
        )
        profile = userPoster.objects.get(userID=payment_user.pk)
        self.assertEqual(profile.contact, "customer@example.com")
        self.assertEqual(profile.signedFrom, f"paymongo:{self.source.slug}")
        self.assertEqual(payment_user.additionalCreds_id, profile.pk)

        user_subscription = UserSubscription.objects.get(receipt_number=transaction.internal_reference_id)
        self.assertEqual(user_subscription.user_id, payment_user.pk)
        self.assertEqual(user_subscription.plan_id, self.plan.pk)
        self.assertEqual(user_subscription.email, "customer@example.com")
        self.assertEqual(user_subscription.status, "ACTIVE")
        self.assertEqual(user_subscription.subscription_status, "ACTIVE")
        self.assertEqual(user_subscription.last_payment_amount_value, Decimal("499.00"))
        self.assertEqual(user_subscription.last_payment_amount_currency, "PHP")
        self.assertEqual(profile.user_subscription_id, user_subscription.pk)

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

    def test_subscription_updated_cancelled_deactivates_user_subscription(self):
        User = get_user_model()
        payment_user = User.objects.create_user(username="cancelled@example.com", email="cancelled@example.com")
        customer = Customer.objects.create(
            source_website=self.source,
            email="cancelled@example.com",
            paymongo_customer_id="cus_cancelled_123",
        )
        transaction = Transaction.objects.create(
            source_website=self.source,
            product=self.product,
            plan=self.plan,
            payment_button=self.button,
            customer=customer,
            customer_email="cancelled@example.com",
            amount=self.plan.price,
            amount_centavos=49900,
            currency="PHP",
            status="paid",
            paymongo_subscription_id="subs_cancelled_123",
        )
        subscription = Subscription.objects.create(
            customer=customer,
            source_website=self.source,
            plan=self.plan,
            transaction=transaction,
            status="active",
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
            paymongo_subscription_id="subs_cancelled_123",
        )
        user_subscription = UserSubscription.objects.create(
            user=payment_user,
            plan=self.plan,
            email="cancelled@example.com",
            status="ACTIVE",
            subscription_status="ACTIVE",
            paymongo_customer_id="cus_cancelled_123",
            paymongo_subscription_id="subs_cancelled_123",
            receipt_number=transaction.internal_reference_id,
            next_billing_time=subscription.current_period_end,
        )
        payload = {
            "data": {
                "id": "evt_subscription_cancelled",
                "type": "event",
                "attributes": {
                    "type": "subscription.updated",
                    "data": {
                        "id": "subs_cancelled_123",
                        "type": "subscription",
                        "attributes": {
                            "customer_id": "cus_cancelled_123",
                            "plan_id": "plan_paymongo_123",
                            "status": "cancelled",
                            "cancelled_at": int(time.time()),
                            "next_billing_schedule": None,
                        },
                    },
                },
            }
        }
        raw_body, signature_header = self._signed_webhook(payload)

        response = self.client.post(
            reverse("subscription:paymongo_webhook"),
            data=raw_body,
            content_type="application/json",
            HTTP_PAYMONGO_SIGNATURE=signature_header,
        )

        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        user_subscription.refresh_from_db()
        transaction.refresh_from_db()
        self.assertEqual(subscription.status, "cancelled")
        self.assertFalse(subscription.is_active)
        self.assertEqual(user_subscription.status, "CANCELLED")
        self.assertEqual(user_subscription.subscription_status, "CANCELLED")
        self.assertFalse(user_subscription.billing_info["access_enabled"])
        self.assertEqual(user_subscription.billing_info["last_paymongo_event_type"], "subscription.updated")
        self.assertEqual(transaction.status, "paid")
        self.assertEqual(PayMongoWebhookEvent.objects.get(paymongo_event_id="evt_subscription_cancelled").transaction_id, transaction.pk)

    def test_subscription_invoice_payment_failed_suspends_user_access(self):
        User = get_user_model()
        payment_user = User.objects.create_user(username="pastdue@example.com", email="pastdue@example.com")
        customer = Customer.objects.create(
            source_website=self.source,
            email="pastdue@example.com",
            paymongo_customer_id="cus_pastdue_123",
        )
        transaction = Transaction.objects.create(
            source_website=self.source,
            product=self.product,
            plan=self.plan,
            payment_button=self.button,
            customer=customer,
            customer_email="pastdue@example.com",
            amount=self.plan.price,
            amount_centavos=49900,
            currency="PHP",
            status="paid",
            paymongo_subscription_id="subs_pastdue_123",
        )
        subscription = Subscription.objects.create(
            customer=customer,
            source_website=self.source,
            plan=self.plan,
            transaction=transaction,
            status="active",
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
            paymongo_subscription_id="subs_pastdue_123",
        )
        user_subscription = UserSubscription.objects.create(
            user=payment_user,
            plan=self.plan,
            email="pastdue@example.com",
            status="ACTIVE",
            subscription_status="ACTIVE",
            paymongo_customer_id="cus_pastdue_123",
            paymongo_subscription_id="subs_pastdue_123",
            receipt_number=transaction.internal_reference_id,
            failed_payments_count=0,
        )
        payload = {
            "data": {
                "id": "evt_invoice_failed",
                "type": "event",
                "attributes": {
                    "type": "subscription.invoice.payment_failed",
                    "data": {
                        "id": "inv_failed_123",
                        "type": "invoice",
                        "attributes": {
                            "amount": 49900,
                            "currency": "PHP",
                            "customer_id": "cus_pastdue_123",
                            "subscription_id": "subs_pastdue_123",
                            "payment_intent_id": "pi_failed_invoice_123",
                            "status": "open",
                        },
                    },
                },
            }
        }
        raw_body, signature_header = self._signed_webhook(payload)

        response = self.client.post(
            reverse("subscription:paymongo_webhook"),
            data=raw_body,
            content_type="application/json",
            HTTP_PAYMONGO_SIGNATURE=signature_header,
        )

        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        user_subscription.refresh_from_db()
        self.assertEqual(subscription.status, "past_due")
        self.assertFalse(subscription.is_active)
        self.assertEqual(user_subscription.status, "PAST_DUE")
        self.assertEqual(user_subscription.subscription_status, "PAST_DUE")
        self.assertEqual(user_subscription.failed_payments_count, 1)
        self.assertFalse(user_subscription.billing_info["access_enabled"])
        self.assertEqual(user_subscription.billing_info["last_paymongo_invoice_id"], "inv_failed_123")
        self.assertEqual(user_subscription.billing_info["last_paymongo_payment_intent_id"], "pi_failed_invoice_123")

    def test_paid_webhook_creates_user_from_paymongo_payload_email(self):
        transaction = Transaction.objects.create(
            source_website=self.source,
            product=self.product,
            plan=self.plan,
            payment_button=self.button,
            amount=self.plan.price,
            amount_centavos=49900,
            currency="PHP",
            paymongo_checkout_session_id="cs_payload_email",
        )
        payload = {
            "data": {
                "id": "evt_payload_email",
                "attributes": {
                    "type": "checkout_session.payment.paid",
                    "data": {
                        "id": "cs_payload_email",
                        "type": "checkout_session",
                        "attributes": {
                            "status": "paid",
                            "billing": {"email_address": "payload@example.com"},
                            "metadata": {
                                "internal_reference_id": transaction.internal_reference_id,
                                "source_website": self.source.slug,
                                "product_id": str(self.product.pk),
                                "plan_id": str(self.plan.pk),
                            },
                        },
                    },
                },
            }
        }
        raw_body, signature_header = self._signed_webhook(payload)

        response = self.client.post(
            reverse("subscription:paymongo_webhook"),
            data=raw_body,
            content_type="application/json",
            HTTP_PAYMONGO_SIGNATURE=signature_header,
        )

        self.assertEqual(response.status_code, 200)
        transaction.refresh_from_db()
        self.assertEqual(transaction.customer_email, "payload@example.com")
        self.assertEqual(transaction.customer.email, "payload@example.com")
        self.assertTrue(Customer.objects.filter(email="payload@example.com", source_website=self.source).exists())

        User = get_user_model()
        payment_user = User.objects.get(email="payload@example.com")
        self.assertEqual(payment_user.username, "payload@example.com")
        self.assertTrue(
            UserCredentialsBackUP.objects.filter(
                userID=payment_user.pk,
                userPassword__startswith="paymongo:",
            ).exists()
        )
        profile = userPoster.objects.get(userID=payment_user.pk, contact="payload@example.com")
        user_subscription = UserSubscription.objects.get(receipt_number=transaction.internal_reference_id)
        self.assertEqual(user_subscription.user_id, payment_user.pk)
        self.assertEqual(user_subscription.email, "payload@example.com")
        self.assertEqual(profile.user_subscription_id, user_subscription.pk)

    def test_link_paid_webhook_creates_transaction_from_payment_link_reference(self):
        self.button.checkout_mode = "paymongo_link"
        self.button.payment_link_url = "https://pm.link/org-LE2YAQrsDm1hi7RJFcdVrj1r/b5vnlvt"
        self.button.payment_link_reference = "b5vnlvt"
        self.button.save(update_fields=["checkout_mode", "payment_link_url", "payment_link_reference"])
        payload = {
            "data": {
                "id": "evt_link_paid",
                "attributes": {
                    "type": "link.payment.paid",
                    "data": {
                        "id": "link_test_123",
                        "type": "link",
                        "attributes": {
                            "amount": 49900,
                            "currency": "PHP",
                            "checkout_url": "https://pm.link/org-LE2YAQrsDm1hi7RJFcdVrj1r/b5vnlvt",
                            "reference_number": "b5vnlvt",
                            "status": "paid",
                            "payments": [
                                {
                                    "data": {
                                        "id": "pay_link_123",
                                        "type": "payment",
                                        "attributes": {
                                            "amount": 49900,
                                            "currency": "PHP",
                                            "billing": {
                                                "email": "link-paid@example.com",
                                                "name": "Link Customer",
                                                "phone": "09171234567",
                                                "address": {
                                                    "line1": "123 Test Street",
                                                    "line2": "Unit 4",
                                                    "city": "Makati",
                                                    "state": "Metro Manila",
                                                    "postal_code": "1229",
                                                    "country": "PH",
                                                },
                                            },
                                            "external_reference_number": "b5vnlvt",
                                            "payment_intent_id": "pi_link_123",
                                            "status": "paid",
                                        },
                                    }
                                }
                            ],
                        },
                    },
                },
            }
        }
        raw_body, signature_header = self._signed_webhook(payload)

        response = self.client.post(
            reverse("subscription:paymongo_webhook"),
            data=raw_body,
            content_type="application/json",
            HTTP_PAYMONGO_SIGNATURE=signature_header,
        )

        self.assertEqual(response.status_code, 200)
        transaction = Transaction.objects.get()
        self.assertEqual(transaction.payment_button_id, self.button.pk)
        self.assertEqual(transaction.status, "paid")
        self.assertEqual(transaction.paymongo_link_id, "link_test_123")
        self.assertEqual(transaction.paymongo_reference_number, "b5vnlvt")
        self.assertEqual(transaction.paymongo_payment_id, "pay_link_123")
        self.assertEqual(transaction.paymongo_payment_intent_id, "pi_link_123")
        self.assertEqual(transaction.customer_email, "link-paid@example.com")
        self.assertEqual(transaction.customer_name, "Link Customer")
        self.assertEqual(transaction.customer_phone, "09171234567")
        self.assertEqual(transaction.customer_billing_details["address"]["city"], "Makati")

        customer = Customer.objects.get(email="link-paid@example.com")
        self.assertEqual(customer.source_website_id, self.source.pk)
        self.assertEqual(customer.name, "Link Customer")
        self.assertEqual(customer.phone, "09171234567")
        self.assertEqual(customer.metadata["paymongo_billing"]["address"]["country"], "PH")
        subscription = Subscription.objects.get(customer=customer)
        self.assertEqual(subscription.status, "active")
        self.assertEqual(subscription.transaction_id, transaction.pk)

        User = get_user_model()
        payment_user = User.objects.get(email="link-paid@example.com")
        self.assertTrue(UserCredentialsBackUP.objects.filter(userID=payment_user.pk).exists())
        user_subscription = UserSubscription.objects.get(receipt_number=transaction.internal_reference_id)
        self.assertEqual(user_subscription.user_id, payment_user.pk)
        self.assertEqual(user_subscription.mobile_number, "09171234567")
        self.assertEqual(user_subscription.subscriber["address"]["city"], "Makati")
        profile = userPoster.objects.get(userID=payment_user.pk)
        self.assertEqual(profile.mobile_number, "09171234567")
        self.assertEqual(profile.address_line1, "123 Test Street")
        self.assertEqual(profile.address_city, "Makati")
        self.assertEqual(profile.address_country, "PH")
        self.assertEqual(profile.paymongo_billing_details["address"]["postal_code"], "1229")

    @patch("subscription.views.PayMongoClient.retrieve_checkout_session")
    def test_success_return_syncs_paid_checkout_when_webhook_is_missing(self, mocked_retrieve):
        transaction = Transaction.objects.create(
            source_website=self.source,
            product=self.product,
            plan=self.plan,
            payment_button=self.button,
            amount=self.plan.price,
            amount_centavos=49900,
            currency="PHP",
            paymongo_checkout_session_id="cs_success_sync",
            status="checkout_created",
        )
        mocked_retrieve.return_value = {
            "data": {
                "id": "cs_success_sync",
                "type": "checkout_session",
                "attributes": {
                    "status": "paid",
                    "billing": {"email": {"unexpected": "nested object"}},
                    "metadata": {
                        "internal_reference_id": transaction.internal_reference_id,
                        "source_website": self.source.slug,
                        "product_id": str(self.product.pk),
                        "plan_id": str(self.plan.pk),
                    },
                    "payments": [
                        {
                            "id": "pay_success_sync",
                            "type": "payment",
                            "attributes": {
                                "billing": {"email": "success-sync@example.com"},
                            },
                        }
                    ],
                    "payment_intent": {
                        "id": "pi_success_sync",
                        "type": "payment_intent",
                        "attributes": {"status": "succeeded"},
                    },
                },
            }
        }

        response = self.client.get(
            reverse("subscription:paymongo_success", args=[transaction.internal_reference_id])
        )

        self.assertEqual(response.status_code, 200)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, "paid")
        self.assertEqual(transaction.customer_email, "success-sync@example.com")
        self.assertEqual(transaction.paymongo_payment_id, "pay_success_sync")
        self.assertEqual(transaction.paymongo_payment_intent_id, "pi_success_sync")
        self.assertTrue(
            PayMongoWebhookEvent.objects.filter(
                paymongo_event_id=f"sync_cs_success_sync_{transaction.internal_reference_id}",
                event_type="checkout_session.payment.paid",
                verified=True,
                processing_status="processed",
            ).exists()
        )

        customer = Customer.objects.get(email="success-sync@example.com")
        self.assertEqual(customer.source_website_id, self.source.pk)
        subscription = Subscription.objects.get(customer=customer)
        self.assertEqual(subscription.status, "active")

        User = get_user_model()
        payment_user = User.objects.get(email="success-sync@example.com")
        self.assertTrue(
            UserCredentialsBackUP.objects.filter(
                userID=payment_user.pk,
                userPassword__startswith="paymongo:",
            ).exists()
        )
        user_subscription = UserSubscription.objects.get(receipt_number=transaction.internal_reference_id)
        profile = userPoster.objects.get(userID=payment_user.pk)
        self.assertEqual(user_subscription.user_id, payment_user.pk)
        self.assertEqual(profile.user_subscription_id, user_subscription.pk)

    @patch("subscription.views.PayMongoClient.retrieve_checkout_session")
    def test_success_return_does_not_500_when_sqlite_is_locked_during_sync(self, mocked_retrieve):
        transaction = Transaction.objects.create(
            source_website=self.source,
            product=self.product,
            plan=self.plan,
            payment_button=self.button,
            amount=self.plan.price,
            amount_centavos=49900,
            currency="PHP",
            paymongo_checkout_session_id="cs_locked_sync",
            status="checkout_created",
        )
        mocked_retrieve.return_value = {
            "data": {
                "id": "cs_locked_sync",
                "type": "checkout_session",
                "attributes": {
                    "status": "paid",
                    "metadata": {
                        "internal_reference_id": transaction.internal_reference_id,
                        "source_website": self.source.slug,
                        "product_id": str(self.product.pk),
                        "plan_id": str(self.plan.pk),
                    },
                    "payments": [
                        {
                            "id": "pay_locked_sync",
                            "type": "payment",
                            "attributes": {
                                "billing": {"email": "locked-sync@example.com"},
                                "status": "paid",
                            },
                        }
                    ],
                },
            }
        }

        with patch(
            "subscription.views.PayMongoWebhookEvent.objects.get_or_create",
            side_effect=OperationalError("database is locked"),
        ):
            response = self.client.get(
                reverse("subscription:paymongo_success", args=[transaction.internal_reference_id])
            )

        self.assertEqual(response.status_code, 200)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, "checkout_created")

    @patch("subscription.views.PayMongoClient.retrieve_checkout_session")
    def test_paid_success_return_logs_in_user_and_redirects_to_source_success_url(self, mocked_retrieve):
        self.source.default_success_url = "http://testserver/userProfile/"
        self.source.save(update_fields=["default_success_url"])
        transaction = Transaction.objects.create(
            source_website=self.source,
            product=self.product,
            plan=self.plan,
            payment_button=self.button,
            amount=self.plan.price,
            amount_centavos=49900,
            currency="PHP",
            paymongo_checkout_session_id="cs_login_redirect",
            status="checkout_created",
        )
        mocked_retrieve.return_value = {
            "data": {
                "id": "cs_login_redirect",
                "type": "checkout_session",
                "attributes": {
                    "status": "paid",
                    "metadata": {
                        "internal_reference_id": transaction.internal_reference_id,
                        "source_website": self.source.slug,
                        "product_id": str(self.product.pk),
                        "plan_id": str(self.plan.pk),
                    },
                    "payments": [
                        {
                            "id": "pay_login_redirect",
                            "type": "payment",
                            "attributes": {
                                "billing": {"email": "login-redirect@example.com"},
                                "payment_intent_id": "pi_login_redirect",
                                "status": "paid",
                            },
                        }
                    ],
                },
            }
        }

        response = self.client.get(
            reverse("subscription:paymongo_success", args=[transaction.internal_reference_id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://testserver/userProfile/")
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, "paid")
        self.assertEqual(transaction.customer_email, "login-redirect@example.com")

        User = get_user_model()
        payment_user = User.objects.get(email="login-redirect@example.com")
        session = self.client.session
        self.assertEqual(str(session["_auth_user_id"]), str(payment_user.pk))
        self.assertEqual(session["paymongo_last_success"]["transaction_reference"], transaction.internal_reference_id)
        self.assertEqual(session["paymongo_last_success"]["plan_id"], self.plan.pk)
