
from pathlib import Path
from dotenv import load_dotenv
import os
import secrets

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = True # Temporarily set to True for development

ALLOWED_HOSTS = ['*'] if DEBUG else []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'Krushi.apps.KrushiConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.common.BrokenLinkEmailsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'KrushiPro.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'KrushiPro.wsgi.application'


# Django Sites (required by django-allauth)
SITE_ID = 1


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

"""
Database Configuration

Defaults to PostgreSQL when environment variables are provided.
Falls back to SQLite for local development if required variables are missing.
"""

_db_name = os.getenv('DB_NAME')
_db_user = os.getenv('DB_USER')
_db_password = os.getenv('DB_PASSWORD')
_db_host = os.getenv('DB_HOST')
_db_port = os.getenv('DB_PORT')

if all([_db_name, _db_user, _db_password, _db_host, _db_port]):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _db_name,
            'USER': _db_user,
            'PASSWORD': _db_password,
            'HOST': _db_host,
            'PORT': _db_port,
        }
    }
else:
    # SQLite fallback for development/testing
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }




# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Gemini API Key
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Google OAuth (django-allauth)
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')

# Plant.id API configuration
# You can override these via environment variables PLANT_ID_API_KEY and PLANT_ID_BASE_URL
# Defaults are provided based on the user's request.
PLANT_ID_API_KEY = os.getenv('PLANT_ID_API_KEY')
PLANT_ID_BASE_URL = os.getenv('PLANT_ID_BASE_URL')

# OCR.space API (store in .env as OCR_SPACE_API_KEY)
OCR_SPACE_API_KEY = os.getenv('OCR_SPACE_API_KEY', '')

# API Ninjas (Weather) API key
# Store in .env as API_NINJAS_API_KEY=your_key
API_NINJAS_API_KEY = os.getenv('API_NINJAS_API_KEY', '')

# OpenWeather Agromonitoring API key for Seasonal Crop Planning
# Get your free API key from: https://agromonitoring.com/api
AGROMONITORING_API_KEY = os.getenv('AGROMONITORING_API_KEY', '')

# Custom User Model
AUTH_USER_MODEL = 'Krushi.User'


# django-allauth account configuration (updated for latest version)
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_LOGIN_METHODS = {'email', 'username'}

# Custom adapters for seamless OAuth
ACCOUNT_ADAPTER = 'Krushi.adapters.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'Krushi.adapters.CustomSocialAccountAdapter'

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_ON_GET = False

# Social account settings for seamless Google OAuth
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_LOGIN_ON_GET = True  # Allow GET requests to initiate login (direct redirect)



SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': GOOGLE_CLIENT_ID,
            'secret': GOOGLE_CLIENT_SECRET,
            'key': ''
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'VERIFIED_EMAIL': True,
    }
}

# Local ML Model configuration
# Directory containing your trained model artifacts (tokenizer, config, model weights, etc.)
LOCAL_MODEL_DIR = os.getenv('LOCAL_MODEL_DIR', BASE_DIR / 'my_model')

# Force using local model for all requests (overrides client flag)
USE_LOCAL_MODEL = os.getenv('USE_LOCAL_MODEL', 'false').lower() in ('1', 'true', 'yes')

# If API fails, try local model automatically
FALLBACK_TO_LOCAL = os.getenv('FALLBACK_TO_LOCAL', 'true').lower() in ('1', 'true', 'yes')

# Payments: Razorpay (set these in your .env)
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')
RAZORPAY_WEBHOOK_SECRET = os.getenv('RAZORPAY_WEBHOOK_SECRET', '')



# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'thadgesushant@gmail.com'
EMAIL_HOST_PASSWORD = 'dwcwipevrqhzfwns'  # App Password
DEFAULT_FROM_EMAIL = 'thadgesushant@gmail.com'
