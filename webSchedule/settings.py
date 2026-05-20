import os
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url
from decouple import config
from dotenv import load_dotenv


def _split_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


# Ensure environment variables from the project-level .env are available via os.getenv.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=False)

OPENAI_API_KEY = config("OPENAI_API_KEY", default="")

GROK_API_KEY = os.getenv('GROK_API_KEY')

# GROK_MODEL_NAME = config("GROK_MODEL_NAME", default="grok-4")
GROK_MODEL_NAME_EXPENSIVE = config("GROK_MODEL_NAME", default="grok-4")
GROK_MODEL_NAME = config("GROK_MODEL_NAME", default="grok-4.3")
XAI_IMAGE_MODEL = 'grok-imagine-image-quality' 
# Replace the DATABASES section of your settings.py with this
X_FRAME_OPTIONS = 'SAMEORIGIN'
CSRF_COOKIE_SAMESITE = None
# Force HTTPS redirect

SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # ✅ Expire session when the browser closes
SESSION_COOKIE_AGE = 1209600  
SESSION_SAVE_EVERY_REQUEST = True
APPEND_SLASH = True
# heroku trust for ip


# DEBUG = os.getenv('DEBUG', 'False') == 'True'
# DEBUG = os.getenv('DEBUG', 'False') == 'True'
# DEBUG = os.getenv('DEBUG', 'False') == 'True'
DEBUG = config("DEBUG", default=True, cast=bool)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

def skip_static_requests(record):
    try:
        msg = record.args[0]
        if isinstance(msg, str):
            return not msg.startswith('GET /static/')
    except Exception:
        pass
    return True  # Default: do not skip
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        # use Django's built in CallbackFilter to point to your filter 
        'skip_static_requests': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': skip_static_requests
        }
    },
    'formatters': {
        # django's default formatter — use SafeServerFormatter to ensure server_time exists
        'django.server': {
            '()': 'webSchedule.logging_utils.SafeServerFormatter',
            'format': '[%(server_time)s] %(message)s',
        }
    },
    'handlers': {
        # django's default handler...
        'django.server': {
            'level': 'INFO',
            'filters': ['skip_static_requests'],  # <- ...with one change
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
    },
    'loggers': {
        # django's default logger
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}
# ---------------------------------------------
# Cache settings
# In dev (DEBUG=True), default is NO caching so pages/data stay fresh.
# To toggle without editing code:
# - Disable: export ENABLE_SITE_CACHE=0
# - Enable:  export ENABLE_SITE_CACHE=1
ENABLE_SITE_CACHE = os.getenv("ENABLE_SITE_CACHE", "0" if DEBUG else "1") == "1"

if not ENABLE_SITE_CACHE:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }
else:
    if os.getenv('REDIS_URL'):
        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": os.getenv('REDIS_URL'),
                "OPTIONS": {
                    "CLIENT_CLASS": "django_redis.client.DefaultClient",
                    "CONNECTION_POOL_KWARGS": {"max_connections": 50},
                    "SOCKET_CONNECT_TIMEOUT": 5,
                    "SOCKET_TIMEOUT": 5,
                },
                "KEY_PREFIX": "paratara",
                "TIMEOUT": 300,
            }
        }
    else:
        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "unique-snowflake",
            }
        }

# Cache middleware settings
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 600 if ENABLE_SITE_CACHE else 0
CACHE_MIDDLEWARE_KEY_PREFIX = 'paratara'
# ---------------------------------------------


IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "65ed182b008522d2c762031a3ff4953b")
SEMAPHORE_API_KEY = "d143175c87ef8d34892002f91838e75e"
TWILIO_ACCOUNT_SID = "AC399079d8a6451adf9101db54846fa291"
TWILIO_AUTH_TOKEN = "be7efdf77d17897a382fba5c3a78ea65"
TWILIO_PHONE_NUMBER = "+17656663702"
TWILIO_RECOVERY = "7DD7XW9846U21JHWR81MRH8Q"
_default_csrf_trusted_origins = [
    'http://localhost:8000',
    'http://localhost:8000/',
    'https://paratara.com',
    'http://paratara.com',
    'https://www.paratara.com',
    'http://www.paratara.com',
    'https://*.herokuapp.com',
    'https://4dbc-114-108-200-246.ngrok-free.app',
    'https://cc0a-114-108-200-246.ngrok-free.app',
    'https://dayojohn19-django.prod1.defang.dev',
    'https://31ce4dc9652b.ngrok-free.app'
]
PYTHONANYWHERE_DOMAIN = config("PYTHONANYWHERE_DOMAIN", default="").strip()
CSRF_TRUSTED_ORIGINS = _default_csrf_trusted_origins + _split_csv(
    config("CSRF_TRUSTED_ORIGINS", default="")
)
if PYTHONANYWHERE_DOMAIN:
    CSRF_TRUSTED_ORIGINS.extend(
        [
            f"https://{PYTHONANYWHERE_DOMAIN}",
            f"http://{PYTHONANYWHERE_DOMAIN}",
        ]
    )
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))


CLIENT_S_FILE = 'thermal-list-338806-4603674b3ae6.json'
GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE = CLIENT_S_FILE
"""
Django settings for webSchedule project.

Generated by 'django-admin startproject' using Django 3.2.6.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
# BASE_DIR = Path(__file__).resolve().parent.parent
GEOIP_PATH = os.path.join(BASE_DIR, "geoip")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config(
    "SECRET_KEY",
    default='django-insecure-v(_$6u5l=&_#2zejvc2--yeq2r!p09atdef1&-!$-are$^g46p',
)

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = False
# wew

ALLOWED_HOSTS = _split_csv(
    config(
        "ALLOWED_HOSTS",
        default="localhost,127.0.0.1,paratara.com,www.paratara.com,digitallife11.pythonanywhere.com,,www.ourblueearth.online,ourblueearth.online",
    )
)
if PYTHONANYWHERE_DOMAIN and PYTHONANYWHERE_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(PYTHONANYWHERE_DOMAIN)


#
# BASE_DIR = Path(__file__).resolve().parent

# TAILWINDCSS_CLI_FILE = BASE_DIR / 'tailwind.config.js'
# TAILWINDCSS_CONFIG_FILE = BASE_DIR / 'tailwind.config.js'

# # For file mode
# TAILWINDCSS_OUTPUT_FILE = ''
# File upload size limits — 20-30 Canon photos ~8 MB each ≈ 240 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 400 * 1024 * 1024   # 400 MB — covers large multipart batches
FILE_UPLOAD_MAX_MEMORY_SIZE = 1 * 1024 * 1024     # 1 MB  — spool to disk quickly; saves RAM

# Application
INSTALLED_APPS = [
    'subscription',
    'imageapp',
    'resortManagement',
    # "tailwindcss",
    'garden',
    'calculator',
    'singlepage2',
    'apis.apps.ApisConfig',
    "corsheaders",
    'rest_framework',
    'home.apps.HomeConfig',
    'userProfile',
    'resorts',
    # 'daphne',
    # 'djongo',
    # 'app_Car',
    'django.contrib.humanize',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'social_django',  # add this for social app authentication
    "django_extensions",  # for localhost https run
    #  python manage.py runserver_plus --cert-file cert.pem --key-file key.pem
    # 'gdstorage', # just removed
    # SiteMap TODO https://learndjango.com/tutorials/django-sitemap-tutorial

    "django.contrib.sites",  # new TODO
    'django.contrib.sitemaps'
]
SITE_ID = 1  # new

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

if ENABLE_SITE_CACHE:
    MIDDLEWARE += [
        'django.middleware.cache.UpdateCacheMiddleware',  # Cache middleware (first)
    ]

MIDDLEWARE += [
    "corsheaders.middleware.CorsMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'userProfile.middleware.RequestMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # Compression
    'webSchedule.middleware.NotFoundIPBlockMiddleware',
    'webSchedule.middleware.SimpleThrottleMiddleware',
]

if ENABLE_SITE_CACHE:
    MIDDLEWARE += [
        'django.middleware.cache.FetchFromCacheMiddleware',  # Cache middleware (last)
    ]
# Enable WhiteNoise compression for static files
# Using CompressedStaticFilesStorage instead of CompressedManifestStaticFilesStorage
# to avoid errors with missing referenced files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

ROOT_URLCONF = 'webSchedule.urls'
SETTINGS_PATH = os.path.dirname(os.path.dirname(__file__))
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(SETTINGS_PATH, 'templates')],
        # 'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.tz',
                'home.context_processors.navbar_context',
                # 'social_django.context_processors.backends',
                # 'social_django.context_processors.login_redirect',  # added
            ],
        },
    },
]

ASGI_APPLICATION = 'webSchedule.asgi.application'
WSGI_APPLICATION = 'webSchedule.wsgi.application'
 


tmpPostgres = urlparse('postgresql://proj2db_owner:5wp7PSktMcyL@ep-sparkling-recipe-a1ivtzqm.ap-southeast-1.aws.neon.tech/proj2db?sslmode=require')
# BEING USED SEPTEMBER 2025 - Optimized for Heroku - Using Neon Database
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': tmpPostgres.path.replace('/', ''),
#         'USER': tmpPostgres.username,
#         'PASSWORD': tmpPostgres.password,
#         'HOST': tmpPostgres.hostname,
#         'PORT': 5432,
#         'CONN_MAX_AGE': 600,  # Persistent connections
#         'OPTIONS': {
#             'connect_timeout': 10,
#             'options': '-c statement_timeout=30000',  # 30 second timeout
#         },
#     }
# }
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'proj2local',
#         'USER': 'nhoj',      # your local postgres user
#         'PASSWORD': '',       # leave blank if none
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }
# ----------------------------------------------------------------------------
# --------------------- FOR PRODUCTION 
#  ------------------------------
# ----------------------------------------------------------------------------
# # # DEFAULT Database
# # https://docs.djangoproject.com/en/3.2/ref/settings/#databases
DATABASE_URL = config("DATABASE_URL", default="").strip()
SQLITE_DB_NAME = config("SQLITE_DB_NAME", default="db.sqlite3")
DATABASE_URL = False
if DATABASE_URL:
    database_config = dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=DATABASE_URL.startswith("postgres"),
    )
    if database_config.get("ENGINE") == "django.db.backends.sqlite3":
        database_config.setdefault("OPTIONS", {})
        database_config["OPTIONS"]["timeout"] = 30
    DATABASES = {"default": database_config}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / SQLITE_DB_NAME,
            'OPTIONS': {
                'timeout': 30,
            },
        }
    }

# DATABASES = {'default': dj_database_url.config(default='postgres://u2vmde7teu8uk8:p1c1f6b91f06e8163d79eb47b7bf74a3c07b1e4850af4793e9385020f38207630@c38j9kbm97l2pa.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com:5432/ddubfgoh2q9f5b',ssl_require=True)}

# DATABASES = {
#     'default': dj_database_url.config(
#         default=os.environ.get('postgres://u2vmde7teu8uk8:p1c1f6b91f06e8163d79eb47b7bf74a3c07b1e4850af4793e9385020f38207630@c38j9kbm97l2pa.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com:5432/ddubfgoh2q9f5b'),
#         conn_max_age=600,
#         ssl_require=True
#     )
# }
# DATABASES = {
#     'default': dj_database_url.config(
#         default=os.environ.get('postgres://u2vmde7teu8uk8:p1c1f6b91f06e8163d79eb47b7bf74a3c07b1e4850af4793e9385020f38207630@c38j9kbm97l2pa.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com:5432/ddubfgoh2q9f5b'),
#         conn_max_age=600,
#         ssl_require=True
#     )
# }

# DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
# STATICFILES_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
"""
# MONGODB   ***********************
----------------------------------------------------------------------------
----------------------------------------------------------------------------
------------------- USING THIS FOR DATABASE OFFICIAL -----------------------
----------------------------------------------------------------------------
----------------------------------------------------------------------------
"""
# import dj_database_url``
# DATABASES['default']
# from pymongo.mongo_client import MongoClient
# uri = "mongodb+srv://websiteprojects:nUihAXEQpGVJombK@cluster0.38ndv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# uri = 'mongodb+srv://websiteprojects:nUihAXEQpGVJombK@cluster0.38ndv.mongodb.net/TreepDB?retryWrites=true&w=majority&ssl_cert_reqs=CERT_NONE'
# 'host': 'mongodb+srv://websiteprojects:nUihAXEQpGVJombK@cluster0.38ndv.mongodb.net/TreepDB?retryWrites=true&w=majority&ssl_cert_reqs=CERT_NONE'
# import dj_database_url
# DATABASES['default'] = dj_database_url.config(conn_max_age=600)
# DATABASES['default'] = dj_database_url.config(default='mongodb+srv://websiteprojects:nUihAXEQpGVJombK@cluster0.38ndv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
# client = MongoClient(uri)
# try:
#     client.admin.command('ping')
#     print("Pinged your deployment. You successfully connected to MongoDB!")
# except Exception as e:
#     print(e)
# DATABASES = {
#     'default': {
#         'ENGINE': 'djongo',
#         'NAME': 'TreepDB',
#         # 'ENFORCE_SCHEMA': True,
#         'CLIENT': {
#             'host': 'mongodb+srv://websiteprojects:nUihAXEQpGVJombK@cluster0.38ndv.mongodb.net/TreepDB?retryWrites=true&w=majority&ssl_cert_reqs=CERT_NONE'
#             # 'host':client
            
#             # 'host' : 'mongodb+srv://websiteprojects:nUihAXEQpGVJombK@cluster0.38ndv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"'
#         }

#     }
# }
""" DATA BASE FOR RESORTS / HOME"""
# DATABASES = {
#     'default': {
#         'ENGINE': 'djongo',
#         'NAME': 'cardApiDB',
#         'ENFORCE_SCHEMA': False,
#         'CLIENT': {
#             'host': 'mongodb+srv://websiteprojects:nUihAXEQpGVJombK@cluster0.38ndv.mongodb.net/TreepDB?retryWrites=true&w=majority&ssl_cert_reqs=CERT_NONE'
#         }

#     }
# }
"""
----------------------------------------------------------------------------
----------------------------------------------------------------------------
----------------------------------------------------------------------------
----------------------------------------------------------------------------
"""
# **********************************************
# **********************************************
# **********************************************
# **********************************************

# RESTORING FILES FORM MONGO DB
# mongorestore --uri "mongodb+srv://websiteprojects:nUihAXEQpGVJombK@cluster0.38ndv.mongodb.net/TreepDB" ./mongo-backup
# mongodump --uri "mongodb+srv://Admin:MYPASS@appcluster.15lf4.mongodb.net/mytestdb" -o ./mongo-backup
# authenticate user from


# AMAZON DATABASE

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': 'postgres',
#         'USER': 'postgres',
#         'PASSWORD': '_-[#Ml4D[F){Iz!igKXmf.l-Ca)4',
#         # 'HOST': 'END_POINT',
#         'HOST': 'mytreepdb.c1yxjrvkibvp.ap-southeast-1.rds.amazonaws.com',
#         'PORT': '5432',
#     }
# }


AUTH_USER_MODEL = 'userProfile.UserCredentials'
# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.2/topics/i18n/

# LANGUAGE_CODE = 'en-us'
LANGUAGE = "en_US.UTF-8"


        
TIME_ZONE = 'Asia/Manila'
# TIME_ZONE = 'UTC'
# USE_TZ = True 

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
#
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    # os.path.join(BASE_DIR, 'resorts/static/'),
    os.path.join(BASE_DIR / "static"),
    # os.path.join(BASE_DIR / "singlepage2/static"),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


AUTHENTICATION_BACKENDS = [
    # 'social_core.backends.facebook.FacebookOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]
LOGIN_URL = 'userProfile:loginUser'
LOGIN_REDIRECT_URL = 'userProfile:profile'
LOGOUT_URL = 'urserProfile:logoutUser'
LOGOUT_REDIRECT_URL = 'userProfile:profile'
# SOCIAL_AUTH_FACEBOOK_KEY = '499005982203937'
# SOCIAL_AUTH_FACEBOOK_SECRET = '48c26680446a831c1f6900561b1eb6fc'
# SOCIAL_AUTH_FACEBOOK_SCOPE = ['email','public_profile']
# Added till below
# SOCIAL_AUTH_FACEBOOK_SCOPE = ['email', 'user_link', 'public_profile']
# SOCIAL_AUTH_FACEBOOK_PROFILE_EXTRA_PARAMS = {
#     'fields': 'id, name, email, picture.type(large), link'
# }
# SOCIAL_AUTH_FACEBOOK_EXTRA_DATA = [
#     ('name', 'name'),
#     ('email', 'email'),
#     ('picture', 'picture'),
#     ('link', 'profile_url'),
# ]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "https://example.com",
    "https://sub.example.com",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
]
# PAYPAL_CLIENT_ID = ""
# PAYPAL_SECRET = ""
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "AREL4vTRiJV97jXqNzJkFn2dwjMsUhdmsFRORX5yv8WnqErFYPh7gi1Qy8UVm3KY1TS_DmZCRSzougyu")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET", "EBATrMJahBR--ZgQUj_VsJu5mF0fbHfJqLIKJZwaD4MzzX2mx5N3hzMn42B")
PAYPAL_WEBHOOK_URL = os.getenv("PAYPAL_WEBHOOK_URL", "https://paratara.com/paypal/webhook/")
PAYPAL_WEBHOOK_CLIENT = os.getenv("PAYPAL_WEBHOOK_CLIENT", "AW3JSwW3AKeo5P_AZ8F3GonKIoWInUb3ebXxWH4BAm0t7j19CVsN7tskFv_xDVY6iqYyTx_w-S090_y5")

PAYPAL_WEBHOOK_SECRET = os.getenv("PAYPAL_WEBHOOK_SECRET", "EJs3wVccCfoH89HBNsivni9oYssXSHorYsJqmCKYkFyyHdV3hK6jrfaMF8OFCmkotPCO-T7kSCI-wyDh")
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID", "06C44678BC1319848")
PAYPAL_SUBSCRIPTION_PLAN_ID = os.getenv("PAYPAL_SUBSCRIPTION_PLAN_ID", "P-0UE0536194695712WNFHT4TY")
PAYPAL_WEBHOOK_EVENTS = os.getenv("PAYPAL_WEBHOOK_EVENTS", "All Events")
PAYPAL_API_BASE="https://api-m.paypal.com"

# PAYPAL_CLIENT_ID = "YOUR_CLIENT_ID"
# PAYPAL_SECRET = "YOUR_SECRET"
# PAYPAL_WEBHOOK_ID = "YOUR_WEBHOOK_ID"

# PAYPAL_API_BASE = "https://api-m.sandbox.paypal.com"  # sandbox
# PAYPAL_API_BASE = "https://api-m.paypal.com"  # live
CLOUDINARY = {
  "cloud_name": "dzsiogux5",
  "api_key": "957222581381515",
  "api_secret": "C96MmoxWVIiFg58BwJ4mjpRsgZA"
}
# CLOUDINARY_URL=cloudinary://<your_api_key>:<your_api_secret>@dzsiogux5
CLOUDINARY_URL = 'cloudinary://957222581381515:C96MmoxWVIiFg58BwJ4mjpRsgZA@dzsiogux5'