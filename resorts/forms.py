from django import forms
from .models import resortItem,resortPackages,sideImagesURLs,Packages

from django.forms import ModelForm, Textarea
 


from .models import resortItem
from userProfile.models import userPoster







# class ResortFormv2(forms.Form):
#     headerPhoto = forms.FileField()
#     owner = forms.ModelMultipleChoiceField(queryset=userPoster.objects.all())
    
    # class Meta:
    #     model=resortItem

    
    #     fields = ['owner','name']
    # widgets = {
    #     'name':forms.TextInput(attrs={'class':'form-control'}),
    #     'owner':forms.Select(attrs={'class':'form-control'}),
        
    # }
    
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.name = forms.ModelChoiceField(queryset=userPoster.objects.all()) # TODO change queryset to filter verified=True
# formset = resortItemFormSet(queryset=resortItem.objects.all())

# class BaseAuthorFormSet(BaseModelFormSet):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args,**kwargs)
#         self.queryset = resortItem.objects.all()
class matterURLform(forms.Form):
    # widget=forms.FileInput(attrs={'class': 'rounded_list'})
    # urlInputarea = forms.FileField(attrs={'onchange':'alert("Its working")'})
    thismatter = forms.FileField(required=False,widget=forms.FileInput(attrs={'onchange': 'console.log("Its working")','onchange':'console.log("working ONclick)','type':'file'}))
    thismatter2 = forms.URLField(
    required=False,
    widget=forms.URLInput(attrs={
        'placeholder': 'Photo URL or Upload',
        'id': 'thismatter2'   # <-- added ID here
    })
)
    # this.form.submit


class ResortForm(forms.ModelForm):
    class Meta:
        model = resortItem
        fields = ('place','province','RealName','address','contactNumber','contactEmail','whatsappNumber','open_hours','promotionalVideo','latitude','longitude','description', 
                  'has_wifi','has_pool','has_bidet','has_parking','has_restaurant','has_bar','has_spa','has_gym',
                  'has_beach_access','has_air_conditioning','has_hot_water','has_breakfast','has_laundry',
                  'pet_friendly','family_friendly','has_generator',
                  'accepts_gcash','accepts_cash','accepts_debit_card','accepts_credit_card')
        fields.__class__('form-control')
        
        widgets = {
            'place': forms.Select(attrs={'class': 'form-control'}),
            'adminManager': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'province':forms.TextInput(attrs={'placeholder':'where','class':'form-control'}),
            # 'registeredBy':forms.TextInput(attrs={'class':'form-control'}),
            'province':forms.TextInput(attrs={'class':'form-control'}),
            'RealName':forms.TextInput(attrs={'class':'form-control'}),
            'address':forms.TextInput(attrs={'class':'form-control'}),
            'contactNumber':forms.TextInput(attrs={'class':'form-control'}),
            'contactEmail':forms.TextInput(attrs={'class':'form-control'}),
            'whatsappNumber':forms.TextInput(attrs={'class':'form-control'}),
            'open_hours': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mon–Sun 8:00 AM – 9:00 PM',
            }),
            'promotionalVideo':forms.TextInput(attrs={'placeholder':'Get From embed video Link in Youtube','class':'form-control'}),
            # 'headerImage':forms.TextInput(attrs={'class':'form-control'}),
            'description':forms.TextInput(attrs={'class':'form-control'}),
            'latitude':forms.TextInput(attrs={'placeholder':'12.1234','class':'form-control'}),
            'longitude':forms.TextInput(attrs={'placeholder':'123.1234','class':'form-control'}),
            'virtualpicture':forms.TextInput(attrs={'class':'form-control'}),
            # Amenity checkboxes
            'has_wifi':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_pool':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_bidet':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_parking':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_restaurant':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_bar':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_spa':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_gym':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_beach_access':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_air_conditioning':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_hot_water':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_breakfast':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_laundry':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'pet_friendly':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'family_friendly':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'has_generator':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            # Payment methods
            'accepts_gcash':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'accepts_cash':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'accepts_debit_card':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'accepts_credit_card':forms.CheckboxInput(attrs={'class':'form-check-input'}),
            
        }
        labels = {
            'place':'Location / Place',
            'province':'Province',
            'RealName':' Establishment Name',
            'address':' Address',
            'contactNumber':'Contact Number',
            'contactEmail':'Establishment Email',
            'whatsappNumber':'WhatsApp Number',
            'open_hours': 'Open Hours',
            'promotionalVideo':'Promotional Video Link',
            # 'headerImage':'Resort Main Image Link',
            'description':' Brief Description',
            'virtualpicture':'Virtual Pic Link',
            # Amenity labels
            'has_wifi':'Free WiFi',
            'has_pool':'Swimming Pool',
            'has_bidet':'Bidet in CR',
            'has_parking':'Parking Available',
            'has_restaurant':'Restaurant',
            'has_bar':'Bar/Lounge',
            'has_spa':'Spa Services',
            'has_gym':'Gym/Fitness Center',
            'has_beach_access':'Beach Access',
            'has_air_conditioning':'Air Conditioning',
            'has_hot_water':'Hot Water',
            'has_breakfast':'Breakfast Available',
            'has_laundry':'Laundry Service',
            'pet_friendly':'Pet Friendly',
            'family_friendly':'Family Friendly',
            'has_generator':'Backup Generator',
            # Payment method labels
            'accepts_gcash':'Accepts GCash',
            'accepts_cash':'Accepts Cash',
            'accepts_debit_card':'Accepts Debit Card',
            'accepts_credit_card':'Accepts Credit Card',
        }
        help_texts = {
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        # Exclude current instance when editing
        queryset = resortItem.objects.filter(name=name)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError(f"Resort URL name '{name}' already exists. Please choose a different name.")
        return name

    def clean_RealName(self):
        real_name = self.cleaned_data.get('RealName')
        # Exclude current instance when editing
        queryset = resortItem.objects.filter(RealName=real_name)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError(f"Resort name '{real_name}' already exists. Please choose a different name.")
        return real_name

    def save(self, commit=True):
        instance = super().save(commit=commit)
        # On create via form, also add resort to the selected place's resort list
        try:
            if commit and instance.place:
                instance.place.resortItem.add(instance)
        except Exception:
            # Avoid surfacing form errors due to linkage; signal also handles linking
            pass
        return instance
