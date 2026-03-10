from django import forms
from .models import User

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['name','email','password']


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class CropForm(forms.Form):
    nitrogen = forms.FloatField()
    phosphorus = forms.FloatField()
    potassium = forms.FloatField()
    ph = forms.FloatField()