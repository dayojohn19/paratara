from django import forms
from .models import ImageUploadsModel


class ImgUploadForm(forms.Form):
    image = forms.ImageField(required=True)

class UserImageForm(forms.ModelForm):
    class Meta:
        model = ImageUploadsModel
        fields = ('title', 'image')
 