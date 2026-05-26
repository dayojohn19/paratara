# PayMongo Subscription Flow

## 1. Configure Django

Set these environment variables on the Django payment server:

```bash
PAYMONGO_SECRET_KEY=
PAYMONGO_PUBLIC_KEY=
PAYMONGO_WEBHOOK_SECRET=
PAYMONGO_MODE=test
PAYMONGO_CHECKOUT_API_VERSION=v1
PAYMONGO_ENABLE_RECURRING=False
DJANGO_PAYMENT_BASE_URL=https://www.paratara.com
PAYMONGO_ALLOWED_PAYMENT_METHODS=card,gcash,paymaya,grab_pay,qrph
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

## 5. Django Creates PayMongo Checkout

Django sends a backend-only request to PayMongo Checkout Sessions using the configured secret key.

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
- `payment.paid`
- `payment.failed`
- `payment.refunded`
- `payment.refund.updated`

Django verifies `Paymongo-Signature` using `PAYMONGO_WEBHOOK_SECRET`.

## 8. Django Processes Webhook Idempotently

Django stores each PayMongo event in `PayMongoWebhookEvent`.

Duplicate event ids are ignored and return success without reprocessing.

For successful payment events:

1. Django finds the transaction by `internal_reference_id` metadata or PayMongo ids.
2. Transaction status becomes `paid`.
3. PayMongo ids and raw payload are stored.
4. A local `Subscription` is activated or extended.

For failure/cancel/refund events:

1. Transaction status is updated.
2. Raw payload is stored.
3. Refunded subscriptions linked to the transaction are cancelled.

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
