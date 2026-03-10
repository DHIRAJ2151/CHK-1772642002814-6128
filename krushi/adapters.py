from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model
import re

User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to handle Google OAuth signup seamlessly
    """
    
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a social provider,
        but before the login is actually processed.
        """
        # If user is already logged in, just connect the account
        if request.user.is_authenticated:
            return
        
        # Check if user exists with this email
        if sociallogin.is_existing:
            return
        
        # Try to connect to existing user by email
        try:
            email = sociallogin.account.extra_data.get('email', '').lower()
            if email:
                user = User.objects.get(email__iexact=email)
                sociallogin.connect(request, user)
        except User.DoesNotExist:
            pass
    
    def populate_user(self, request, sociallogin, data):
        """
        Populate user information from social provider data
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Get data from Google
        extra_data = sociallogin.account.extra_data
        
        # Set first and last name
        if not user.first_name:
            user.first_name = extra_data.get('given_name', '')
        if not user.last_name:
            user.last_name = extra_data.get('family_name', '')
        
        # Generate username from email if not set
        if not user.username:
            email = data.get('email', '')
            if email:
                # Create username from email (before @)
                base_username = email.split('@')[0]
                # Clean username (only alphanumeric and underscore)
                base_username = re.sub(r'[^\w]', '_', base_username)
                
                # Ensure username is unique
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user.username = username
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Save the user and mark them as a farmer by default
        """
        user = super().save_user(request, sociallogin, form)
        
        # Set default farmer flag
        if not hasattr(user, 'is_farmer') or user.is_farmer is None:
            user.is_farmer = True
            user.save()
        
        return user


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter for account management
    """
    
    def is_open_for_signup(self, request):
        """
        Allow signups
        """
        return True
    
    def save_user(self, request, user, form, commit=True):
        """
        Save user with custom fields
        """
        user = super().save_user(request, user, form, commit=False)
        
        # Set default farmer flag
        if not hasattr(user, 'is_farmer') or user.is_farmer is None:
            user.is_farmer = True
        
        if commit:
            user.save()
        
        return user
