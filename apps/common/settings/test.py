from apps.common.settings.base import *

DEBUG = True
SECRET_KEY = "Test secret"
ALLOWED_HOSTS = ["*"]
TEMPLATES[0]["OPTIONS"]["auto_reload"] = DEBUG

# Required for django-debug-toolbar
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# Event Bus Configuration
EVENT_BUS = {
    'BACKEND': 'apps.event_hub.services.backends.django_q.DjangoQBackend',
    'LOGGING_ENABLED': True,
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_db',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
        'TEST': {
            'NAME': 'test_db',
        },
    }
}

# Django Q Configuration
Q_CLUSTER = {
    'name': 'test_cluster',
    'workers': 4,
    'timeout': 30,
    'orm': 'default',  # Use Django ORM as broker
    'sync': True,  # Run tasks synchronously in tests
    'testing': True
}
