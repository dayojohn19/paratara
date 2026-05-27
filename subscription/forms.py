from urllib.parse import urlparse

from django import forms
from django.utils.text import slugify

from .models import PaymentButton, SourceWebsite, SubscriptionPlan, SubscriptionProduct


class SourceWebsiteForm(forms.ModelForm):
    allowed_origins_text = forms.CharField(
        label="Allowed origins",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "https://example.com\nhttps://www.example.com",
            }
        ),
        help_text="One origin per line. Include scheme, for example https://example.com.",
    )

    class Meta:
        model = SourceWebsite
        fields = [
            "name",
            "slug",
            "active",
            "default_success_url",
            "default_cancel_url",
            "default_failed_url",
            "notes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["allowed_origins_text"].initial = "\n".join(self.instance.allowed_origins or [])

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or self.cleaned_data.get("name") or ""
        return slugify(slug)

    def clean_allowed_origins_text(self):
        raw_value = self.cleaned_data.get("allowed_origins_text") or ""
        return [line.strip().rstrip("/") for line in raw_value.splitlines() if line.strip()]

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.allowed_origins = self.cleaned_data.get("allowed_origins_text", [])
        if commit:
            obj.save()
        return obj


class SubscriptionProductForm(forms.ModelForm):
    class Meta:
        model = SubscriptionProduct
        fields = [
            "name",
            "description",
            "product_type",
            "category",
            "status",
            "paymongo_product_id",
        ]


class SubscriptionPlanForm(forms.ModelForm):
    features_text = forms.CharField(
        label="Features",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "One feature per line"}),
    )

    class Meta:
        model = SubscriptionPlan
        fields = [
            "name",
            "slug",
            "description",
            "price",
            "currency",
            "billingInterval",
            "type",
            "status",
            "subscriptionProduct",
            "paymongo_plan_id",
            "imageUrl",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subscriptionProduct"].required = False
        if self.instance and self.instance.pk:
            self.fields["features_text"].initial = "\n".join(self.instance.features or [])

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or self.cleaned_data.get("name") or ""
        return slugify(slug)

    def clean_currency(self):
        return (self.cleaned_data.get("currency") or "PHP").upper()

    def clean_features_text(self):
        raw_value = self.cleaned_data.get("features_text") or ""
        return [line.strip() for line in raw_value.splitlines() if line.strip()]

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.features = self.cleaned_data.get("features_text", [])
        if commit:
            obj.save()
            if obj.subscriptionProduct:
                obj.subscriptionProduct.subscription_plans.add(obj)
        return obj


class PaymentButtonForm(forms.ModelForm):
    class Meta:
        model = PaymentButton
        fields = [
            "source_website",
            "product",
            "plan",
            "label",
            "description",
            "checkout_mode",
            "active",
            "success_url",
            "cancel_url",
            "failed_url",
            "payment_link_url",
            "payment_link_reference",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source_website"].queryset = SourceWebsite.objects.filter(active=True).order_by("name")
        self.fields["product"].queryset = SubscriptionProduct.objects.order_by("name")
        self.fields["plan"].queryset = SubscriptionPlan.objects.filter(status="active").order_by("price", "name")
        self.fields["payment_link_url"].required = False
        self.fields["payment_link_reference"].required = False

    def clean_payment_link_reference(self):
        reference = (self.cleaned_data.get("payment_link_reference") or "").strip()
        return reference or None

    def clean(self):
        cleaned_data = super().clean()
        checkout_mode = cleaned_data.get("checkout_mode")
        payment_link_url = (cleaned_data.get("payment_link_url") or "").strip()
        payment_link_reference = cleaned_data.get("payment_link_reference")

        if checkout_mode == "paymongo_link":
            if not payment_link_url:
                self.add_error("payment_link_url", "Payment link URL is required for PayMongo Payment Link buttons.")
            if not payment_link_reference and payment_link_url:
                parsed_path = urlparse(payment_link_url).path.rstrip("/")
                payment_link_reference = parsed_path.rsplit("/", 1)[-1] if parsed_path else ""
                cleaned_data["payment_link_reference"] = payment_link_reference or None
            if not payment_link_reference:
                self.add_error("payment_link_reference", "Reference number is required for PayMongo Payment Link buttons.")

        if payment_link_reference:
            duplicate_qs = PaymentButton.objects.filter(
                checkout_mode="paymongo_link",
                payment_link_reference__iexact=payment_link_reference,
            )
            if self.instance and self.instance.pk:
                duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)
            if duplicate_qs.exists():
                self.add_error("payment_link_reference", "A PayMongo Payment Link button with this reference already exists.")

        return cleaned_data
