"""
Django settings for Clusive PRODUCTION and QA servers.
This file is read when the DJANGO_CONFIG environment variable is set to "prod".
"""
import os

# SECURITY WARNING: keep the secret key used in production secret!
# Key not set here; must be set from environment variable.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Note, this MEDIA_ROOT is expected by entrypoint.sh - if you change it here, check there too.
MEDIA_ROOT = '/app/uploads'
MEDIA_URL = '/uploads/'

#######################
# SECURITY MIDDLEWARE #
#######################
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True


ALLOWED_HOSTS = ['clusive.cast.org',
                 'clusive.qa.cast.org',
                 'clusive.stage.cast.org',
                 'localhost',
                 '127.0.0.1',
                 '[::1]']

ACCOUNT_DEFAULT_HTTP_PROTOCOL='https'

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

if os.environ.get('DJANGO_ADMIN_EMAIL'):
    ADMINS = [os.environ.get('DJANGO_ADMIN_NAME'), os.environ.get('DJANGO_ADMIN_EMAIL')]

DEFAULT_FROM_EMAIL  = os.environ.get('DJANGO_DEFAULT_EMAIL', 'cisl@cast.org')
SERVER_EMAIL        = os.environ.get('DJANGO_SERVER_EMAIL', 'cisl@cast.org')

EMAIL_HOST          = os.environ.get('DJANGO_EMAIL_HOST', 'localhost')
EMAIL_PORT          = os.environ.get('DJANGO_EMAIL_PORT', '25')
EMAIL_HOST_USER     = os.environ.get('DJANGO_EMAIL_USER', None)
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_PASSWORD', None)
EMAIL_USE_TLS       = os.environ.get('DJANGO_EMAIL_TLS', False)
EMAIL_USE_SSL       = os.environ.get('DJANGO_EMAIL_SSL', False)
