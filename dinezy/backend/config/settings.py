import os
import secrets
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = BACKEND_DIR.parent
FRONTEND_DIR = BASE_DIR / 'frontend'


def _load_env_file(path):
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(BASE_DIR / '.env')


def env(key, default=''):
    nilai = os.environ.get(key)
    if nilai is None and key.startswith('DINEZY_'):
        nilai = os.environ.get('NSC_' + key[7:])
    return default if nilai is None else nilai


def env_bool(key, default=False):
    return env(key, str(default)).lower() in ('1', 'true', 'yes', 'ya', 'on')


def env_list(key, default=''):
    return [x.strip() for x in env(key, default).split(',') if x.strip()]


def _secret_key(debug):
    key = env('DINEZY_SECRET_KEY')
    if key and (debug or (len(key) >= 40 and not key.startswith('ganti-'))):
        return key
    path = BASE_DIR / '.secret_key'
    if path.exists():
        return path.read_text(encoding='utf-8').strip()
    key = secrets.token_urlsafe(64)
    path.write_text(key, encoding='utf-8')
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key


DEBUG = env_bool('DINEZY_DEBUG', True)
SECRET_KEY = _secret_key(DEBUG)
ALLOWED_HOSTS = env_list('DINEZY_ALLOWED_HOSTS', '*' if DEBUG else 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('DINEZY_CSRF_TRUSTED_ORIGINS', '')
DINEZY_TRUST_PROXY = env_bool('DINEZY_TRUST_PROXY', False)
DINEZY_ADMIN_PATH = env('DINEZY_ADMIN_PATH', 'admin/').strip('/') + '/'

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.security.SecurityHeadersMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'core.middleware.DatabaseErrorMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [FRONTEND_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.brand',
                'core.context_processors.admin_stats',
                'core.context_processors.ketentuan_denda',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DB_ENGINE = env('DINEZY_DB_ENGINE', 'sqlite' if env('DINEZY_USE_SQLITE') == '1' else 'mysql').lower()

if DB_ENGINE == 'mysql':
    import pymysql

    pymysql.install_as_MySQLdb()
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': env('DINEZY_DB_NAME', 'db_dinezy'),
            'USER': env('DINEZY_DB_USER', 'root'),
            'PASSWORD': env('DINEZY_DB_PASSWORD', ''),
            'HOST': env('DINEZY_DB_HOST', '127.0.0.1'),
            'PORT': env('DINEZY_DB_PORT', '3306'),
            'CONN_MAX_AGE': int(env('DINEZY_DB_CONN_MAX_AGE', '60')),
            'CONN_HEALTH_CHECKS': True,
            'ATOMIC_REQUESTS': False,
            'OPTIONS': {
                'charset': 'utf8mb4',
                'connect_timeout': 10,
                'isolation_level': 'read committed',
                'init_command': "SET sql_mode='STRICT_ALL_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,"
                                "NO_ENGINE_SUBSTITUTION'",
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / env('DINEZY_SQLITE_FILE', 'db.sqlite3'),
        }
    }

DINEZY_AUTO_MIGRATE = env_bool('DINEZY_AUTO_MIGRATE', True)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / 'var' / 'cache',
        'TIMEOUT': 3600,
        'OPTIONS': {'MAX_ENTRIES': 5000},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
DINEZY_LOGIN_MAKS_GAGAL = int(env('DINEZY_LOGIN_MAKS_GAGAL', '5'))
DINEZY_LOGIN_KUNCI_MENIT = int(env('DINEZY_LOGIN_KUNCI_MENIT', '15'))
DINEZY_DAFTAR_MAKS_PER_JAM = int(env('DINEZY_DAFTAR_MAKS_PER_JAM', '20'))

LANGUAGE_CODE = 'id-id'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [FRONTEND_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DINEZY_SERVE_FILES = env_bool('DINEZY_SERVE_FILES', True)

DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 400
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = int(env('DINEZY_SESSION_JAM', '12')) * 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_FAILURE_VIEW = 'core.views.csrf_failure'

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'SAMEORIGIN'

DINEZY_HTTPS = env_bool('DINEZY_HTTPS', not DEBUG and bool(CSRF_TRUSTED_ORIGINS))
if DINEZY_HTTPS:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool('DINEZY_SSL_REDIRECT', True)
    SECURE_HSTS_SECONDS = int(env('DINEZY_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DINEZY_HSTS_SUBDOMAINS', False)
    SECURE_HSTS_PRELOAD = False
if DINEZY_TRUST_PROXY:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CORS_ALLOWED_ORIGINS = env_list('DINEZY_CORS_ORIGINS', '')
CORS_ALLOW_ALL_ORIGINS = DEBUG and not CORS_ALLOWED_ORIGINS
CORS_URLS_REGEX = r'^/api/.*$'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer']
                                + (['rest_framework.renderers.BrowsableAPIRenderer'] if DEBUG else []),
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': env('DINEZY_API_ANON_RATE', '300/min'),
        'user': env('DINEZY_API_USER_RATE', '600/min'),
    },
}

JAZZMIN_SETTINGS = {
    'site_title': 'Dinezy',
    'site_header': 'Dinezy',
    'site_brand': 'Dinezy · Data Lanjutan',
    'site_logo': 'core/img/dinezy-mark-white.png',
    'login_logo': 'core/img/dinezy-mark-navy.png',
    'site_icon': 'core/img/favicon-64.png',
    'welcome_sign': 'Data Lanjutan Dinezy',
    'custom_css': 'core/jazzmin.css',
    'copyright': 'PT Nuwus Multikreasi Digital',
    'search_model': ['core.Tenant'],
    'show_sidebar': True,
    'navigation_expanded': True,
    'hide_models': ['core.Order', 'core.Menu', 'auth.Group'],
    'custom_links': {
        'core': [
            {'name': 'Keuangan', 'url': 'admin:index', 'icon': 'fas fa-chart-line'},
            {'name': 'Tagihan Biaya Aplikasi', 'url': 'admin:index', 'icon': 'fas fa-file-invoice-dollar'},
        ]
    },
    'icons': {'core.tenant': 'fas fa-store', 'auth.user': 'fas fa-user-shield'},
    'order_with_respect_to': ['core.Tenant', 'auth.user'],
    'topmenu_links': [
        {'name': '← Panel Admin', 'url': '/panel/'},
        {'name': 'Tagihan', 'url': '/panel/tagihan/'},
    ],
}

JAZZMIN_UI_TWEAKS = {
    'navbar': 'navbar-dark',
    'brand_colour': 'navbar-dark',
    'sidebar': 'sidebar-dark-primary',
    'accent': 'accent-navy',
    'no_navbar_border': True,
    'button_classes': {'primary': 'btn-primary', 'secondary': 'btn-outline-secondary'},
}

EMAIL_BACKEND = env('DINEZY_EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('DINEZY_EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(env('DINEZY_EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 15
EMAIL_HOST_USER = env('DINEZY_EMAIL_USER', '')
EMAIL_HOST_PASSWORD = env('DINEZY_EMAIL_PASSWORD', '')
DEFAULT_FROM_EMAIL = f'Dinezy <{EMAIL_HOST_USER or "no-reply@localhost"}>'

LOGIN_URL = '/login/'

DINEZY_TARIF_PER_NOTA = int(env('DINEZY_TARIF_PER_NOTA', '1500'))
DINEZY_DENDA_TENGGANG_HARI = int(env('DINEZY_DENDA_TENGGANG_HARI', '3'))
DINEZY_DENDA_PERMIL_HARI = float(env('DINEZY_DENDA_PERMIL_HARI', '1'))
DINEZY_DENDA_MAKS_PERSEN = float(env('DINEZY_DENDA_MAKS_PERSEN', '10'))
DINEZY_BILLING_START = env('DINEZY_BILLING_START', '2026-11')

DINEZY_NAMA = env('DINEZY_NAMA', 'Dinezy')
DINEZY_TAGLINE = env('DINEZY_TAGLINE', 'Smarter Dining, Made Easy')
DINEZY_DESKRIPSI = env('DINEZY_DESKRIPSI', 'QR Ordering & Payment Platform for Restaurants and Cafés')

DINEZY_PERUSAHAAN_NAMA = env('DINEZY_PERUSAHAAN_NAMA', 'PT NUWUS MULTIKREASI DIGITAL')
DINEZY_PERUSAHAAN_ALAMAT = env('DINEZY_PERUSAHAAN_ALAMAT', 'Jl. Sumbersari Gg. 4 No. 286A, RT 008/RW 001, Kel. Sumbersari, '
                                                     'Kec. Lowokwaru, Kota Malang, Jawa Timur 65145')
DINEZY_PERUSAHAAN_SK = env('DINEZY_PERUSAHAAN_SK', 'AHU-A139487.AH.01.30.Tahun 2026')
DINEZY_PERUSAHAAN_NIB = env('DINEZY_PERUSAHAAN_NIB', '')
DINEZY_PERUSAHAAN_WAKIL = env('DINEZY_PERUSAHAAN_WAKIL', 'M. Faza Musyaffa Al Azizi')
DINEZY_PERUSAHAAN_JABATAN = env('DINEZY_PERUSAHAAN_JABATAN', 'Direktur')
DINEZY_PERUSAHAAN_EMAIL = env('DINEZY_PERUSAHAAN_EMAIL', 'nuwusmultikreasi@gmail.com')
DINEZY_PERUSAHAAN_WA = env('DINEZY_PERUSAHAAN_WA', '089684608866')
DINEZY_PENGADILAN = env('DINEZY_PENGADILAN', 'Pengadilan Negeri Malang')
DINEZY_PKS_BATAS_HARI = int(env('DINEZY_PKS_BATAS_HARI', '14'))

DINEZY_PAYMENT_BANK = env('DINEZY_PAYMENT_BANK', 'Bank BRI')
DINEZY_PAYMENT_ACCOUNT = env('DINEZY_PAYMENT_ACCOUNT', '0000-01-000000-00-0')
DINEZY_PAYMENT_NAME = env('DINEZY_PAYMENT_NAME', 'PT Nuwus Multikreasi Digital')
DINEZY_ADMIN_WA = env('DINEZY_ADMIN_WA', '6289654551912')
DINEZY_COMPANY_ADDRESS = env('DINEZY_COMPANY_ADDRESS', 'Malang, Jawa Timur')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'std': {'format': '%(asctime)s %(levelname)s %(name)s: %(message)s'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'std'}},
    'loggers': {
        'core': {'handlers': ['console'], 'level': 'INFO'},
        'django.security': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
