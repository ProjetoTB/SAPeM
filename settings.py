import os

# Django settings for tbForms project.


DEBUG = True
TEMPLATE_DEBUG = DEBUG
SERVER_VERSION = True
COMM_DIR =os.path.join(os.path.expanduser('~'), '.sapem/xml')

if not SERVER_VERSION:
	if not os.path.isdir(COMM_DIR):
		os.makedirs(COMM_DIR)

ADMINS = (
    ('Fernando Ferreira', 'fferreira@icsystems.com.br'),
)

MANAGERS = ADMINS
#Site URL. Please edit if the system is moved
#SITE_ROOT = '/sapem/'
SITE_ROOT = '/~fferreira/sapem/'
#SITE_ROOT = 'http://localhost:8000/'

DATABASES = {
	'default':{
		'ENGINE' : 'django.db.backends.sqlite3',           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
		'NAME' : os.path.join(os.path.dirname(os.path.realpath(__file__)) , 'tb.db')            # Or path to database file if using sqlite3.
		#'USER' : '',             # Not used with sqlite3.
		#'PASSWORD' : '',         # Not used with sqlite3.
		#'HOST' : '' ,            # Set to empty string for localhost. Not used with sqlite3.
		#'PORT' : ''             # Set to empty string for default. Not used with sqlite3.
	}
}
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Sao_Paulo'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'pt-br'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)) , 'custom-media') + '/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = SITE_ROOT + 'custom-media/'

##FIX
#CUSTOM Media prefix
#MEDIA_PREFIX = 

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = SITE_ROOT + 'media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'udzx9q+!1x@1#i(a^^lct-@s4dxqk(uk)5r9kvifr88+jspxxz'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

# Custom user  profile
AUTH_PROFILE_MODULE = 'forms.UserProfile'

#       user's models
# ----> This was commented 'cause it refers to an old way of extending the
# AUTHENTICATION_BACKENDS = (
#	'tbForms.auth_backends.CustomUserModelBackend',
#)
#CUSTOM_USER_MODEL = 'forms.UserProfile'


MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'tbForms.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
	'%s'%(os.path.join(os.path.dirname(os.path.realpath(__file__)) , 'templates'),),
)

INSTALLED_APPS = (
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.sites',
	'tbForms.forms',
	'tbForms.autocomplete',
	'django.contrib.admin',
	'tbForms.reports',
)

TEMPLATE_CONTEXT_PROCESSORS = (
	"django.contrib.auth.context_processors.auth",
	"django.core.context_processors.debug",
	"django.core.context_processors.i18n",
	"django.core.context_processors.media",
	"django.contrib.messages.context_processors.messages",
	"tbForms.contextprocessor.siteroot")
