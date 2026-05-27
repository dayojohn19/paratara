# PayMongo Subscription Flow

## 1. Configure Django

Set these environment variables on the Django payment server:

```bash
PAYMONGO_=sk_test_xxx
PAYMONGO_PUBLIC_KEY=pk_test_xxx
PAYMONGO_WEBHOOK_SECRET=whsk_xxx
PAYMONGO_MODE=test
PAYMONGO_API_BASE=https://api.paymongo.com
PAYMONGO_CHECKOUT_API_VERSION=v1
PAYMONGO_ENABLE_RECURRING=True
PAYMONGO_CREATE_CUSTOMER_RESOURCE=True
PAYMONGO_CUSTOMER_API_VERSION=v2
PAYMONGO_ATTACH_CUSTOMER_TO_CHECKOUT=True
PAYMONGO_CHECKOUT_CUSTOMER_ID_FALLBACK=True
PAYMONGO_ALLOWED_PAYMENT_METHODS=card,gcash,paymaya,grab_pay,qrph
PAYMONGO_TIMEOUT=30
PAYMONGO_WEBHOOK_TOLERANCE_SECONDS=300
PAYMONGO_EMBED_TOKEN_MAX_AGE=31536000
DJANGO_PAYMENT_BASE_URL=https://www.paratara.com
PAYMONGO_CORS_ALLOWED_ORIGINS=https://www.paratara.com,https://paratara.com

```

Run:

```bash
python manage.py makemigrations subscription
python manage.py migrate
python manage.py test subscription
```

## 2. Create Setup Records

Open:

```text
https://www.paratara.com/subscription/paymongo/setup/
```

Create:

1. Source Website with each allowed origin, for example `https://standalone-site.com`.
2. Product.
3. Subscription Plan with server-side price and currency.
4. Payment Button linked to the source, product, and plan.

For a PayMongo Dashboard Payment Link, choose `PayMongo Payment Link` as the button checkout mode and enter:

- The PayMongo link URL, for example `https://pm.link/org-.../b5vnlvt`.
- The PayMongo reference number, for example `b5vnlvt`.

Copy the generated embed snippet.

## 3. Embed On A Standalone Website

Use the generated script snippet:

```html
<script src="https://www.paratara.com/subscription/embed/button.js" data-button-id="BUTTON_PUBLIC_ID" data-embed-token="SIGNED_TOKEN"></script>
```

Optional customer attributes can be added when available:

```html
<script
  src="https://www.paratara.com/subscription/embed/button.js"
  data-button-id="BUTTON_PUBLIC_ID"
  data-embed-token="SIGNED_TOKEN"
  data-customer-email="customer@example.com"
  data-customer-name="Customer Name">
</script>
```

The standalone website never receives the PayMongo secret key and never sends price or amount.

## 4. Customer Clicks The Button

The embed script renders a POST form pointing to:

```text
/subscription/pay/<button_public_id>/
```

Django validates:

- Public button id.
- Signed embed token.
- Active source website, plan, and button.
- Browser `Origin` or `Referer` against the source website allowed origins.

Django creates a pending `Transaction` with a generated `internal_reference_id`.

For `PayMongo Payment Link` buttons, Django records the link reference number and redirects the customer to the existing PayMongo link instead of creating a new Checkout Session.

## 5. Django Creates PayMongo Checkout

For Hosted Checkout buttons, Django sends a backend-only request to PayMongo Checkout Sessions using the configured secret key.

The checkout session includes:

- Server-side amount from `SubscriptionPlan.price`.
- Currency from `SubscriptionPlan.currency`.
- Line item name from the plan.
- Success and cancel return URLs.
- PayMongo reference number set to `Transaction.internal_reference_id`.
- Metadata:
  - `source_website`
  - `source_website_id`
  - `product_id`
  - `plan_id`
  - `plan_slug`
  - `customer_email`
  - `internal_reference_id`

The customer is redirected to PayMongo hosted checkout.

For existing PayMongo Payment Link buttons, the payment link was already created in the PayMongo dashboard. Django does not control that link's amount, so the local `SubscriptionPlan.price` should match the PayMongo link amount.

## 6. PayMongo Returns The Customer

Return URLs are:

```text
/subscription/paymongo/success/<internal_reference_id>/
/subscription/paymongo/cancel/<internal_reference_id>/
/subscription/paymongo/failed/<internal_reference_id>/
```

The success page does not activate access by itself. It tells the customer that access activates after webhook verification.

## 7. PayMongo Sends Webhook

Configure the PayMongo dashboard webhook URL:

```text
https://www.paratara.com/subscription/paymongo/webhook/
```

Subscribe to:

- `checkout_session.payment.paid`
- `link.payment.paid`
- `payment.paid`
- `payment.failed`
- `payment.refunded`
- `payment.refund.updated`
- `subscription.activated`
- `subscription.past_due`
- `subscription.unpaid`
- `subscription.updated`
- `subscription.invoice.paid`
- `subscription.invoice.payment_failed`
- `subscription.invoice.created`
- `subscription.invoice.finalized`

Django verifies `Paymongo-Signature` using `PAYMONGO_WEBHOOK_SECRET`.

## 8. Django Processes Webhook Idempotently

Django stores each PayMongo event in `PayMongoWebhookEvent`.

Duplicate event ids are ignored and return success without reprocessing.

When an email is available, Django also creates a PayMongo Customer API resource and stores its id on the local `Customer.paymongo_customer_id`. The PayMongo dashboard Customers page is backed by the newer customer resource, so keep `PAYMONGO_CUSTOMER_API_VERSION=v2` and `PAYMONGO_CREATE_CUSTOMER_RESOURCE=True` if you want payers to appear there.

For Hosted Checkout buttons, Django also sends `customer_id` when creating the Checkout Session if `PAYMONGO_ATTACH_CUSTOMER_TO_CHECKOUT=True`. If PayMongo rejects `customer_id` on the Checkout Session endpoint, Django retries once without it when `PAYMONGO_CHECKOUT_CUSTOMER_ID_FALLBACK=True`, so payment checkout is not blocked.

For existing PayMongo Payment Link buttons, Django cannot attach a customer id before payment because the payment is created inside the PayMongo-hosted link. Django can still create/update local customers and subscriptions from the webhook, but PayMongo dashboard order history for that Customer depends on PayMongo's own Payment Link customer behavior.

For successful payment events:

1. Django finds the transaction by `internal_reference_id` metadata, PayMongo ids, or the stored PayMongo payment link reference number.
2. Transaction status becomes `paid`.
3. PayMongo ids and raw payload are stored.
4. A local `Subscription` is activated or extended.

For failure/cancel/refund events:

1. Transaction status is updated.
2. Raw payload is stored.
3. Refunded subscriptions linked to the transaction are cancelled.

For PayMongo subscription lifecycle events:

1. Django reads `subscription_id`, invoice id, invoice status, payment intent id, and PayMongo subscription status from the webhook payload.
2. Django finds the local `Subscription` and `UserSubscription` by `paymongo_subscription_id`, or by the linked transaction when available.
3. `subscription.updated` with `cancelled` or `incomplete_cancelled` marks local access as cancelled.
4. `subscription.past_due`, `subscription.unpaid`, and `subscription.invoice.payment_failed` suspend local access and store the last PayMongo invoice/payment-intent ids in `billing_info`.
5. `subscription.activated` and `subscription.invoice.paid` restore local access to active.

## 9. Test Mode Checklist

Before live mode:

- Create all setup records in `/subscription/paymongo/setup/`.
- Embed a button on each allowed standalone domain.
- Confirm disallowed domains are rejected.
- Complete a successful PayMongo test checkout.
- Trigger failed/declined payment cases.
- Replay the same webhook payload and confirm no duplicate processing.
- Confirm transaction, subscription, and webhook rows appear in the dashboard.
- Switch `PAYMONGO_MODE=live`, live keys, live webhook secret, and live PayMongo dashboard webhook only after test mode passes.
