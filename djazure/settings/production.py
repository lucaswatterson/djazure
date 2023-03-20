from .base import *

import os

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [os.getenv("HOSTNAME")]

CSRF_TRUSTED_ORIGINS = [f"https://{os.getenv('HOSTNAME')}"]


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "mssql",
        "NAME": os.getenv("DB_NAME"),
        "USER": f"{os.getenv('DB_USER')}@{os.getenv('DB_SERVER')}",
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_FQDN"),
        "PORT": "1433",
        "OPTIONS": {
            "driver": "ODBC Driver 17 for SQL Server",
        },
    },
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_FILE_STORAGE = "storages.backends.azure_storage.AzureStorage"
STATICFILES_STORAGE = "storages.backends.azure_storage.AzureStorage"

AZURE_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
AZURE_CONTAINER = "files"
