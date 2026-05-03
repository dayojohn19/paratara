from django import forms
from .models import googleimagemodel
class ImageForm(forms.ModelForm):
    # image = forms.ImageField()
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields['image'].widget.attrs.update({'class': 'form-control'})    
    """Form for the image model"""
    class Meta:
        model = googleimagemodel
        fields = ('image',)
        widgets = {
            "image": forms.FileInput(attrs={'onchange': "this.form.submit()",'class':"form-control", 'id':"validatedCustomFile" })
        }
        

# class ImageForm(forms.Form):
#     image = forms.ImageField()
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['image'].widget.attrs.update({'class': 'form-control'})