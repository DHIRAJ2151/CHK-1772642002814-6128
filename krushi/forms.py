from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
import re
from .models import User, Feedback, Review, ContactMessage, Product, Category, FertilizerListing

class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form"""
    email = forms.EmailField(required=True)
    phone = forms.CharField(
        max_length=10, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 10-digit mobile number',
            'inputmode': 'numeric',
            'pattern': '[6-9][0-9]{9}',
            'maxlength': '10',
            'title': 'Enter 10-digit mobile number starting with 6, 7, 8, or 9'
        }),
        help_text='Enter 10-digit mobile number (e.g., 9876543210)'
    )
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'address', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        
        # If phone is empty, it's optional so return empty
        if not phone:
            return phone
        
        # Remove any non-digit characters (just in case)
        phone = re.sub(r'\D', '', phone)
        
        # Must be exactly 10 digits
        if len(phone) != 10:
            raise forms.ValidationError(
                f'Phone number must be exactly 10 digits. You entered {len(phone)} digit{"s" if len(phone) != 1 else ""}.'
            )
        
        # Must start with 6, 7, 8, or 9
        if not phone[0] in '6789':
            raise forms.ValidationError(
                f'Phone number must start with 6, 7, 8, or 9. Your number starts with {phone[0]}.'
            )
        
        # Must contain only digits
        if not phone.isdigit():
            raise forms.ValidationError(
                'Phone number must contain only numeric digits (0-9).'
            )
        
        return phone

class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username or Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Try to authenticate with username
            user = authenticate(username=username, password=password)
            if user is None:
                # Try to authenticate with email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if user is None:
                raise forms.ValidationError('Invalid username/email or password.')
            elif not user.is_active:
                raise forms.ValidationError('This account is inactive.')
        
        return self.cleaned_data

class ForgotPasswordForm(forms.Form):
    """Form to request password reset OTP"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email',
            'autofocus': True
        }),
        label='Email Address'
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError('No account found with this email address.')
        return email

class VerifyOTPForm(forms.Form):
    """Form to verify OTP"""
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit OTP',
            'autofocus': True,
            'inputmode': 'numeric',
            'pattern': '[0-9]{6}'
        }),
        label='OTP Code'
    )
    
    def clean_otp(self):
        otp = self.cleaned_data.get('otp')
        if not otp.isdigit():
            raise forms.ValidationError('OTP must contain only numbers.')
        return otp

class ResetPasswordForm(forms.Form):
    """Form to set new password"""
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'autofocus': True
        }),
        label='New Password',
        min_length=8,
        help_text='Password must be at least 8 characters long.'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        label='Confirm Password'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data

class FeedbackForm(forms.ModelForm):
    """Feedback form for rating the website"""
    rating = forms.ChoiceField(
        choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
        widget=forms.RadioSelect,
        required=True
    )
    
    class Meta:
        model = Feedback
        fields = ['name', 'rating', 'comment']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name (Optional)'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us about your experience...'}),
        }

class ReviewForm(forms.ModelForm):
    """Product review form"""
    rating = forms.ChoiceField(
        choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
        widget=forms.RadioSelect,
        required=True
    )
    
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Share your experience with this product...'}),
        }

class ContactForm(forms.ModelForm):
    """Contact form bound to ContactMessage model"""
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email Address'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Phone Number',
                'inputmode': 'numeric',
                'maxlength': '13',
                'pattern': '^(?:\\+91|0)?[6-9]\\d{9}$',
                'title': 'Enter a valid Indian phone number (e.g., 9876543210 or +919876543210)'
            }),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Tell us how we can help you'}),
        }

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if not phone:
            return phone

        if not re.match(r'^(?:\+91|0)?[6-9]\d{9}$', phone):
            raise forms.ValidationError('Enter a valid phone number (e.g., 9876543210 or +919876543210).')

        return phone

class FertilizerListingForm(forms.ModelForm):
    class Meta:
        model = FertilizerListing
        fields = ['fertilizer_name', 'brand', 'quantity', 'unit', 'price', 'location', 'contact_phone', 'description']
        widgets = {
            'fertilizer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Urea / NPK 19-19-19'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brand (optional)'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantity', 'step': '0.01', 'min': '0'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price (₹)', 'step': '0.01', 'min': '0'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City / Village'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any details (packaging, expiry, etc.)'}),
        }


class SellProductForm(forms.ModelForm):
    """Form for users to sell their products"""
    
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'image', 'stock_quantity']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product name',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your product in detail...',
                'required': True
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter price (₹)',
                'min': '0',
                'step': '0.01',
                'required': True
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'required': True
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Available quantity',
                'min': '1',
                'required': True
            }),
        }
        labels = {
            'name': 'Product Name',
            'description': 'Product Description',
            'price': 'Price (₹)',
            'category': 'Category',
            'image': 'Product Image',
            'stock_quantity': 'Stock Quantity',
        }
        help_texts = {
            'image': 'Upload a clear image of your product (JPG, PNG, max 5MB)',
            'price': 'Enter the selling price in Indian Rupees',
            'stock_quantity': 'How many units do you have available?',
        }
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price <= 0:
            raise forms.ValidationError('Price must be greater than zero.')
        if price > 1000000:
            raise forms.ValidationError('Price cannot exceed ₹10,00,000.')
        return price
    
    def clean_stock_quantity(self):
        quantity = self.cleaned_data.get('stock_quantity')
        if quantity < 1:
            raise forms.ValidationError('Stock quantity must be at least 1.')
        if quantity > 10000:
            raise forms.ValidationError('Stock quantity cannot exceed 10,000 units.')
        return quantity
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (5MB limit)
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image file size cannot exceed 5MB.')
            
            # Check file type
            if not image.content_type in ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']:
                raise forms.ValidationError('Only JPG, PNG, and WebP images are allowed.')
        
        return image

class AdminProductForm(forms.ModelForm):
    """Form for admins to create and edit products"""
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'image', 'stock_quantity', 'is_active', 'seller', 'is_approved']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': 'True'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'required': 'True'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'required': 'True'}),
            'category': forms.Select(attrs={'class': 'form-control', 'required': 'True'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'required': 'True'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'seller': forms.Select(attrs={'class': 'form-control'}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
