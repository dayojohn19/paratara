from django import forms
from django.forms import ModelForm

from garden.models import *


class ProvinceForm(ModelForm):
    class Meta:
        model = Province
        fields = '__all__'


class CollectionForm(ModelForm):

    include_heading_title = forms.BooleanField(
        required=False,
        label="Include Heading Title",
        initial=True
    )
    include_qr_code = forms.BooleanField(
        required=False,
        label="Include QR Code",
        initial=True
    )

    def __init__(self, *args, **kwargs):
        super(CollectionForm, self).__init__(*args, **kwargs)
        self.fields['collectionName'].widget = forms.Select(
            choices=Collection.objects.values_list('collectionName', 'collectionName'))



    class Meta:
        # ThemeChoices = {
        #     'red': 'red',
        #     'blue': 'blue',
        #     'green': 'green',
        #     'yellow': 'yellow',
        # }
        model = Collection
        fields = '__all__'
        # fields['collectionName = forms.Select(
        #     choices=Collection.objects.all())
        widgets = {
            'collectionTheme': forms.Select(attrs={'class': 'color-select'})
        }
        # widgets = {
        #     "collectionTheme": forms.Select(choices=ThemeChoices, attrs={'class': 'form-control'}), }


class PlaceProfileForm(ModelForm):
    class Meta:
        model = PlaceProfile
        fields = '__all__'


class VisitorForm(ModelForm):
    class Meta:
        model = Visitor
        fields = '__all__'


# class QRCodeForm(forms.ModelForm):

#     """Form for the image model"""
#     class Meta:
#         model = QRCode
#         # fields = ('qrImage',)
#         fields = '__all__'
#         widgets = {
#             "qrImage": forms.FileInput(attrs={'onchange': "this.form.submit()", 'class': "custom-file-input", 'id': "validatedCustomFile"})
#         }
