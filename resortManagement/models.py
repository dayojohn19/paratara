from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Create your models here.


    
  
class Checkins(models.Model):
    id_picture = models.URLField(blank=True, null=True)
    room = models.ForeignKey('resorts.Packages', on_delete=models.CASCADE, null=True, related_name='room')
    resort = models.ForeignKey('resorts.resortItem', on_delete=models.CASCADE, null=True, related_name='resort')
    checkin_date = models.DateTimeField()
    checkout_date = models.DateTimeField()
    guest_name = models.CharField(max_length=100)
    guest_email = models.EmailField()
    guest_phone = models.CharField(max_length=15)
    special_requests = models.TextField(blank=True, null=True)
    checked_in = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    checked_in_by = models.ForeignKey('resortManagement.ResortManager', on_delete=models.CASCADE, null=True, related_name='checked_in_by')
 
    def __str__(self):
        return f"{self.guest_name} - "
    class Meta:
        verbose_name = "Check-in"
        verbose_name_plural = "Check-ins"
        ordering = ['checkin_date']
        
class CheckinDay(models.Model):
    checkin = models.ForeignKey('resorts.Packages', on_delete=models.CASCADE, related_name="checkin_days")
    day = models.DateField()
    checkinday = models.DateTimeField()
    checkoutday = models.DateTimeField()
    
 
    def __str__(self):
        return f"{self.checkin} - "

class ResortManager(models.Model):
    profile = models.ForeignKey(
        'userProfile.userPoster', on_delete=models.CASCADE, null=True, related_name='resort_manager')
    checked_visitor = models.ManyToManyField(Checkins, related_name='checked_visitor')

    def __str__(self):
        return f"{self.profile} - "

    @property
    def checked_list(self):
        return self.checked_visitor.all()



class ResortSubscription(models.Model):
    class StatusChoices(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PENDING = 'pending', 'Pending'
        CANCELLED = 'cancelled', 'Cancelled'
        EXPIRED = 'expired', 'Expired'
        PAUSED = 'paused', 'Paused'

    resort = models.ForeignKey(
        'resorts.resortItem', on_delete=models.CASCADE, related_name='subscriptions')  # Resort subscriptions

    paypal_subscription_id = models.CharField(max_length=128, blank=True, null=True, unique=True)

    manager = models.ForeignKey(
        'resortManagement.ResortManager', on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=10, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    auto_renew = models.BooleanField(default=False)
    last_payment_reference = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-end_date']

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError('Subscription end date cannot be before the start date.')

    @property
    def is_active(self):
        today = timezone.now().date()
        return (
            self.status == self.StatusChoices.ACTIVE
            and self.start_date <= today <= self.end_date
        )

    @property
    def remaining_days(self):
        today = timezone.now().date()
        if self.end_date and today <= self.end_date:
            return (self.end_date - today).days
        return 0

    def to_dict(self):
        manager = self.manager
        resort_name = getattr(self.resort, 'RealName', None) if self.resort_id else None
        return {
            'id': self.id,
            'resort_id': self.resort_id,
            'resort_name': resort_name,
            'paypal_subscription_id': self.paypal_subscription_id,
            'status': self.status,
            'status_label': self.get_status_display(),
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'auto_renew': self.auto_renew,
            'last_payment_reference': self.last_payment_reference,
            'notes': self.notes,
            'manager_id': manager.id if manager else None,
            'manager_name': str(manager) if manager else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'remaining_days': self.remaining_days,
        }

    def __str__(self):
        return f"Subscription for {self.resort}"
 
# class Room(models.Model):
#     room_package = models.ForeignKey(
#         'resorts.resortPackages', on_delete=models.CASCADE, null=True, related_name='room_package')
#     room_number = models.CharField(max_length=10, unique=True)
#     room_type = models.CharField(max_length=50)
#     capacity = models.IntegerField()
#     price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
#     is_available = models.BooleanField(default=True)

#     def __str__(self):
#         return f"{self.room_number} - {self.room_type}"