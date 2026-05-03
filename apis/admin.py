from django.contrib import admin

# Register your models here.
from .models import Payments,Transaction, Blogger,Blogs, EmailSubscribers

@admin.register(EmailSubscribers)
class EmailSubscribersAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'is_confirmed', 'is_active', 'email_frequency', 'subscribed_date', 'ip_address']
    list_filter = ['is_confirmed', 'is_active', 'email_frequency', 'subscribed_date']
    search_fields = ['email', 'name', 'ip_address']
    readonly_fields = ['subscribed_date', 'confirmed_date', 'unsubscribed_date', 'email_open_count', 'link_click_count']
    
    fieldsets = (
        ('Subscriber Info', {
            'fields': ('email', 'name', 'is_active', 'ip_address')
        }),
        ('Verification', {
            'fields': ('is_confirmed', 'confirmation_token', 'confirmed_date')
        }),
        ('Preferences', {
            'fields': ('email_frequency', 'interested_categories')
        }),
        ('Engagement', {
            'fields': ('last_email_sent', 'email_open_count', 'link_click_count')
        }),
        ('Analytics', {
            'fields': ('source', 'referrer_url', 'user_agent', 'subscribed_date', 'unsubscribed_date', 'unsubscribe_reason'),
            'classes': ('collapse',)
        }),
    )

admin.site.register(Payments)
admin.site.register(Transaction)
admin.site.register(Blogger)
admin.site.register(Blogs)