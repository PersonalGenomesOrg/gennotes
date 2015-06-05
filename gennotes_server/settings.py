"""
Django settings for gennotes_server project.

Generated by 'django-admin startproject' using Django 1.8.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

import os

import dj_database_url
from django.conf import global_settings
from env_tools import apply_env

from .utils import to_bool


# Apply the environment variables in the .env file.
apply_env()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = to_bool('DEBUG', 'true')

# Settings per Heroku instructions:
# https://devcenter.heroku.com/articles/getting-started-with-django
ALLOWED_HOSTS = ['*']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.postgres',
    'django.contrib.staticfiles',
    # Required by django-allauth
    'django.contrib.sites',

    # Main app for the site.
    'gennotes_server',

    # Third party apps
    'allauth',
    'allauth.account',
    'django_extensions',
    'reversion',
    'rest_framework',
    'rest_framework_swagger'
)

TEMPLATE_CONTEXT_PROCESSORS = (
    # Required by 'allauth' template tags
    'django.core.context_processors.request',

    # 'allauth' specific context processors
    'allauth.account.context_processors.account',
) + global_settings.TEMPLATE_CONTEXT_PROCESSORS

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin
    'django.contrib.auth.backends.ModelBackend',

    # 'allauth' specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
) + global_settings.AUTHENTICATION_BACKENDS

MIDDLEWARE_CLASSES = (
    'reversion.middleware.RevisionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'gennotes_server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gennotes_server.wsgi.application'

# Use DATABASE_URL to do database setup, for a local Postgres database it would
# look like: postgres://localhost/database_name
DATABASES = {}

if os.getenv('CI_NAME') == 'codeship':
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test',
        'USER': os.getenv('PG_USER'),
        'PASSWORD': os.getenv('PG_PASSWORD'),
        'HOST': '127.0.0.1',
    }
# Only override the default if there's a database URL specified
elif dj_database_url.config():
    DATABASES['default'] = dj_database_url.config()

PSQL_USER_IS_SUPERUSER = to_bool('PSQL_USER_IS_SUPERUSER', "True")

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

SITE_ID = 1


# Email set up.
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', global_settings.EMAIL_BACKEND)
EMAIL_USE_TLS = to_bool('EMAIL_USE_TLS', str(global_settings.EMAIL_USE_TLS))
EMAIL_HOST = os.getenv('EMAIL_HOST', global_settings.EMAIL_HOST)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', global_settings.EMAIL_HOST_USER)
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD',
                                global_settings.EMAIL_HOST_PASSWORD)
EMAIL_PORT = int(os.getenv('EMAIL_PORT', str(global_settings.EMAIL_PORT)))


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)


# Settings for django-allauth and account interactions.
# Signup and login take both email and username.
# No email confirmation is implemented.
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'

LOGIN_REDIRECT_URL = 'home'
