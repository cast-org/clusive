"""
Django settings for Clusive PRODUCTION and QA servers.
This file is read when the APP_CONFIG environment variable is set to "prod".
"""
import os

# To improve production settings,
# see https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Key not set here; must be set from environment variable.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['clusive.cast.org',
                 'clusive.qa.cast.org',
                 'cisl-demo.qa.cast.org',
                 'localhost',
                 '127.0.0.1',
                 '[::1]']


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DJANGO_DB_NAME', 'clusive'),
        'USER': os.environ.get('DJANGO_DB_USER', 'user'),
        'PASSWORD': os.environ.get('DJANGO_DB_PASSWORD', 'password'),
        'HOST': os.environ.get('DJANGO_DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DJANGO_DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    }
}
