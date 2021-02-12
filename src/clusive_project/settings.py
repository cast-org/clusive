"""
Django settings for Clusive.

Settings will be read from either settings_local or settings_prod as well, as configured below.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
import logging

logger = logging.getLogger(__name__)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',    
    'roster.apps.RosterConfig',
    'pages.apps.PagesConfig',
    'eventlog.apps.EventlogConfig',
    'library.apps.LibraryConfig',    
    'messagequeue.apps.MessageQueueConfig',
    'glossary.apps.GlossaryConfig',
    'authoring.apps.AuthoringConfig',
    'tips.apps.TipsConfig',
    'django_session_timeout.apps.SessionTimeoutConfig',
    'progressbarupload',
    # added for django-allauth:
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # including only Google provider for now, see:
    # https://django-allauth.readthedocs.io/en/latest/installation.html#django
    'allauth.socialaccount.providers.google'
]

SITE_ID = 1 # django-allauth, id of the django_site record

# django-allauth provider specific settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
            'openid',
            'https://www.googleapis.com/auth/classroom.rosters.readonly',
        ],
        'AUTH_PARAMS': {
            'access_type': 'offline'
        },
        # For each OAuth based provider, either add a ``SocialApp``
        # (``socialaccount`` app) containing the required client credentials
        # to the database, or list them here.  Note that it is more secure to
        # create ``SocialApp``s in the database so that the `client_secret`
        # does not show up in github.
        'APP': {
             # values from Google dashboard setup
             # - uri would be 'http://accounts.google.com/o/oauth2/auth?...
             # - the 'client_id` and `secret` values are created by Google
             # when registering Clusive as a OAuth2 Client, see:
             # https://console.developers.google.com/apis/credentials/
            'client_id': '554291169960-repqllu9q9h5loog0hpadr6854fb2oq0.apps.googleusercontent.com',
            'secret': 'HF9GhAcyvHj0l-uEET99GLbx',
            'key': ''
        }
    }
}

# The `allauth` redirect URI from OAuth2 server back to Clusive after a
# successful authorization is set to '/accounts/profile/', passing back the
# access token*.  But, according to the FAQ, that will result in a 404 because
# `allauth` does not implement anything here -- it's up to individual users of
# the `allauth` library to handle the "callback".  Specifically, Clusive needs
# to implement the details of what to do with a successful confirmation from the
# OAuth2 server.  A suggestion from `allauth` is to set the LOGIN_REDIRECT_URL
# to where the app would go after a local successful login:
# https://django-allauth.readthedocs.io/en/latest/faq.html#when-i-attempt-to-login-i-run-into-a-404-on-accounts-profile
# A possible value for Clusive is '/reader', but that doesn't work out of the
# box; it's likely missing session or some other info.  Setting it to '/reader'
# for experimenting.
# * - need to examine the details of the payload sent with the redirect URI to
# see how the access token is transmitted.  It's likely different depending on
# the OAuth2 provider, e.g., Google vs. Github
LOGIN_REDIRECT_URL = '/account/profile'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_session_timeout.middleware.SessionTimeoutMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'clusive_project.middleware.LookupClusiveUserMiddleware',
]

FILE_UPLOAD_HANDLERS = (
    "progressbarupload.uploadhandler.ProgressBarUploadHandler",
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)

PROGRESSBARUPLOAD_INCLUDE_JQUERY = False

ROOT_URLCONF = 'clusive_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'shared/templates'),
            os.path.join(BASE_DIR, 'glossary/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django_settings_export.settings_export',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'clusive_project.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'max_similarity': .9,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# AUTHENTICATION_BACKENDS needed by `django-allauth` solution
AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',
    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "shared/static"),
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Custom logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '[%(asctime)s] %(levelname)-8s %(name)-12s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        }
    }
}

# Settings allowed to be exported
SETTINGS_EXPORT = [
    'DEBUG',
]

# Session settings
SESSION_EXPIRE_SECONDS = 1800   # 30 minutes, in seconds
SESSION_EXPIRE_AFTER_LAST_ACTIVITY = True
SESSION_COOKIE_AGE = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
LOGIN_URL = '/account/login'

# Load appropriate specific settings file
# This is specified by the value of environment variable DJANGO_CONFIG, defaults to settings_local.py
settingsFileName = os.environ.get('DJANGO_CONFIG', 'local')
fullPath = BASE_DIR + "/clusive_project/settings_" + settingsFileName + ".py"
print("Reading settings file: ", fullPath)
exec(open(fullPath).read(), globals())
