
from django import forms
from .models import Checkins

class CheckinForm(forms.ModelForm):
    checkin_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'readonly': 'readonly','class':'read-only-class',})  # 'datetime-local' allows for both date and time input
    )
    
    checkout_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'readonly': 'readonly','class':'read-only-class',})  # Same widget for checkout_datetime
    )
    class Meta:
        model = Checkins
        fields = [
            'room',
            'resort',
            'guest_name',
            'guest_email',
            'guest_phone',
            'special_requests',
            'checkin_date',
            'checkout_date'
        ]
    # room = forms(max_length=100, widget=forms.HiddenInput(), label=None)
    # resort = forms.CharField(max_length=100, widget=forms.HiddenInput(), label=None)
        