from django.forms import ModelForm
from django import forms
from .models import ImageModel


class ImageForm(forms.ModelForm):

    """Form for the image model"""
    class Meta:
        model = ImageModel
        fields = ('image',)
        widgets = {
            "image": forms.FileInput(attrs={'onchange': "this.form.submit()",'class':"custom-file-input", 'id':"validatedCustomFile" })
        }
