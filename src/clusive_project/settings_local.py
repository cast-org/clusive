"""
Django settings for Clusive local development.  Not to be used in production.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', default='#!7*2*das3a9b29vbsv#j*-*2)t)ae&*g!71pz7&q=s!wk9e80')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

MEDIA_ROOT = BASE_DIR + '/uploads'
MEDIA_URL = '/uploads/'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '10.*',
    '[::1]',
    '10.21.12.86'
]

INTERNAL_IPS = [
    '127.0.0.1',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Don't actually send email, just log to console.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'cisl@cast.org'

# To log database queries, change the level here to DEBUG
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'INFO',
    'propagate': False,
}
