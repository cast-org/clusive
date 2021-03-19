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
]

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
SESSION_IDLE_SECONDS = 600      # 10 minutes (in seconds)
SESSION_TIMEOUT_SECONDS = 1500  # 25 minutes
SESSION_EXPIRE_SECONDS = 1800   # 30 minutes
SESSION_EXPIRE_AFTER_LAST_ACTIVITY = True
SESSION_COOKIE_AGE = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
LOGIN_URL = '/account/login'
LOGIN_REDIRECT_URL = '/dashboard'

# Load appropriate specific settings file
# This is specified by the value of environment variable DJANGO_CONFIG, defaults to settings_local.py
settingsFileName = os.environ.get('DJANGO_CONFIG', 'local')
fullPath = BASE_DIR + "/clusive_project/settings_" + settingsFileName + ".py"
print("Reading settings file: ", fullPath)
exec(open(fullPath).read(), globals())
