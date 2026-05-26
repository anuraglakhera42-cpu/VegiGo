from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
import re
from vgapp.models import UserProfile


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address', 'autocomplete': 'email'}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password', 'autocomplete': 'new-password'}), help_text='At least 8 characters with letters and numbers')
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password', 'autocomplete': 'new-password'}))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('This email is already registered')
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1') or ''
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters')
        if not any(char.isdigit() for char in password):
            raise ValidationError('Password must contain at least one number')
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data['email']
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.username = username
        user.email = email
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address', 'autocomplete': 'email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password', 'autocomplete': 'current-password'}))
    remember_me = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}), label='Remember me')


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address', 'autocomplete': 'email'}))

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            raise ValidationError('No active account found with this email address.')
        return email


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password', 'autocomplete': 'new-password'}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password', 'autocomplete': 'new-password'}))


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=999, initial=1, widget=forms.NumberInput(attrs={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '999'}))


class UpdateCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=999, widget=forms.NumberInput(attrs={'class': 'form-control', 'type': 'number'}))
    action = forms.ChoiceField(choices=[('update', 'Update'), ('remove', 'Remove')], required=False)


class CheckoutFormBase(forms.Form):
    full_name = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name', 'autocomplete': 'name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address', 'autocomplete': 'email'}))
    phone = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number (10-15 digits)', 'autocomplete': 'tel'}))
    street_address = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street Address', 'autocomplete': 'street-address'}))
    city = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City', 'autocomplete': 'address-level2'}))
    state = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State', 'autocomplete': 'address-level1'}))
    pincode = forms.CharField(max_length=10, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode (6 digits)', 'autocomplete': 'postal-code'}))
    payment_method = forms.ChoiceField(choices=[('cod', 'Cash on Delivery'), ('card', 'Credit/Debit Card'), ('upi', 'UPI')], widget=forms.RadioSelect(attrs={'class': 'form-check-input'}))
    terms_accepted = forms.BooleanField(required=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}), label='I agree to the terms and conditions')

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        phone_cleaned = re.sub(r'[\s\-]', '', phone)
        if not phone_cleaned.isdigit() or not (10 <= len(phone_cleaned) <= 15):
            raise ValidationError('Please enter a valid phone number (10-15 digits)')
        return phone_cleaned

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode', '')
        if not pincode.isdigit() or len(pincode) != 6:
            raise ValidationError('Pincode must be exactly 6 digits')
        return pincode

    def clean_city(self):
        city = self.cleaned_data.get('city', '').strip()
        if len(city) < 2:
            raise ValidationError('City name must be at least 2 characters')
        return city

    def clean_street_address(self):
        address = self.cleaned_data.get('street_address', '').strip()
        if len(address) < 5:
            raise ValidationError('Address must be at least 5 characters')
        return address

    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name', '').strip()
        if len(full_name) < 2:
            raise ValidationError('Please enter your name')
        return full_name


class UserCheckoutForm(CheckoutFormBase):
    use_default_address = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}), label='Use saved address')


class GuestCheckoutForm(CheckoutFormBase):
    pass


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))

    class Meta:
        model = UserProfile
        fields = ('phone', 'default_address', 'default_city', 'default_state', 'default_pincode')
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone'}),
            'default_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address'}),
            'default_city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'default_state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'default_pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.user.pk)
        if qs.exists():
            raise ValidationError('Another account already uses this email address.')
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile.save()
        return profile
