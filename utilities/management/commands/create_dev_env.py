from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key
import os


class Command(BaseCommand):
    help = "Create a dev.env file with a SECRET_KEY variable"

    # Skip Django system checks
    requires_system_checks = [False]

    def handle(self, *args, **options):
        # Generate a random secret key with Django
        secret_key = get_random_secret_key()

        # Create a new dev.env file with the required secrets for development
        with open(os.path.join(os.getcwd(), "dev.env"), "w") as f:
            f.write(f"SECRET_KEY={secret_key}")
