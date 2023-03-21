import os
import subprocess
import json
from datetime import datetime
import fileinput
import getpass
import re

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Bootstrap a Django Project from the Django on Azure Template"

    def handle(self, *args, **options):
        # Get, Validate, and Transform User Input
        project_name = get_project_name()

        subscription_id = get_subscription_id()

        region = get_azure_region()

        superuser_user = get_superuser_username()

        superuser_password = get_superuser_password()

        unique_id = datetime.now().strftime("%Y%m%d%H%M%S")

        # Update to Project Name
        update_project_files_to_project_name(project_name)

        # Login to Azure
        print("\nLogging in to Azure")

        login = login_to_azure()

        # Create a Service Principal
        print("\nCreating Service Principal")

        create_service_principal = create_service_principal(project_name, subscription_id)

        # Parse the Service Principal JSON
        credentials = create_service_principal.stdout.decode("utf-8").replace("\n", "")
        auth_info = json.loads(credentials)

        # Create Resource Group, Storage Account, and Container for TF Satet
        print("\nCreating Resources to Store Terraform State")
        set_subscription = subprocess.run(
            ["az", "account", "set", "--subscription", f"{subscription_id}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if set_subscription.returncode != 0:
            raise CommandError(f"Error setting Subscription: {set_subscription.stderr.decode()}")

        resource_group_name = f"{project_name}-tf-state-rg"
        create_resource_group = subprocess.run(
            ["az", "group", "create", "-l", f"{region}", "-n", resource_group_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if create_resource_group.returncode != 0:
            raise CommandError(
                f"Error creating Resource Group: {create_resource_group.stderr.decode()}"
            )

        storage_account_name = f"{project_name}storage{unique_id}"[:24]
        create_storage_account = subprocess.run(
            [
                "az",
                "storage",
                "account",
                "create",
                "--name",
                storage_account_name,
                "--resource-group",
                resource_group_name,
                "--location",
                region,
                "--sku",
                "Standard_LRS",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if create_storage_account.returncode != 0:
            raise CommandError(
                f"Error creating Storage Account: {create_storage_account.stderr.decode()}"
            )

        create_container = subprocess.run(
            [
                "az",
                "storage",
                "container",
                "create",
                "--account-name",
                storage_account_name,
                "--name",
                "state",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if create_container.returncode != 0:
            raise CommandError(f"Error creating Container: {create_container.stderr.decode()}")

        # Set GitHub Secrets
        print("\nLogging in to GitHub")

        os.system("gh auth login")

        with open(os.path.join(os.getcwd(), ".env"), "w") as f:
            f.write(f"STATE_RG={resource_group_name}\n")
            f.write(f"STATE_STORAGE_ACCOUNT={storage_account_name}\n")
            f.write(f"ARM_CLIENT_ID={auth_info['clientId']}\n")
            f.write(f"ARM_CLIENT_SECRET={auth_info['clientSecret']}\n")
            f.write(f"ARM_SUBSCRIPTION_ID={auth_info['subscriptionId']}\n")
            f.write(f"ARM_TENANT_ID={auth_info['tenantId']}\n")
            f.write(f"AZURE_CREDENTIALS={credentials}\n")
            f.write(f"PROJECT_NAME={project_name}\n")
            f.write(f"DJANGO_SUPERUSER_USER={superuser_user}\n")
            f.write(f"DJANGO_SUPERUSER_PASSWORD={superuser_password}\n")

        print("\nSetting GitHub Secrets")
        add_azure_credentials_github = subprocess.run(
            ["gh", "secret", "set", "-f", ".env"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if add_azure_credentials_github.returncode != 0:
            raise CommandError(
                f"Error adding secrets to GitHub: {add_azure_credentials_github.stderr.decode()}"
            )


def get_project_name():
    project_name = input("What is the name of your project? (djazure) ") or "djazure"

    if re.match("^[a-z]*$", project_name):
        return project_name

    project_name = re.sub("[^a-z]+", "", project_name)
    project_name = project_name.lower()

    return project_name


def get_subscription_id():
    subscription_id = ""

    while subscription_id == "":
        subscription_id = input("What is your Azure Subscription ID? ")

    subscription_id = subscription_id.replace(" ", "").replace("\n", "")

    return subscription_id


def get_azure_region():
    region = input("Which Azure Region do you want to deploy to? (eastus) ") or "eastus"

    region = region.replace(" ", "").replace("\n", "")
    region.lower()

    return region


def get_superuser_username():
    while True:
        superuser_user = (
            input("What do you want the Superuser's username to be? (admin) ") or "admin"
        )
        superuser_user = superuser_user.lower().replace("\n", "")

        if re.match("^[a-zA-Z_][a-zA-Z0-9_]*$", superuser_user):
            return superuser_user
        else:
            print(
                "Invalid username. Username must be a valid identifier according to Python naming conventions (i.e. can only contain letters, numbers, and underscores, and cannot start with a number). Please try again."
            )


def get_superuser_password():
    while True:
        superuser_password = getpass.getpass("\nWhat do you want the Superuser's password to be? ")
        superuser_password_confirm = getpass.getpass("Confirm the Superuser's password. ")

        if re.match("^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$", superuser_password):
            if superuser_password == superuser_password_confirm:
                return superuser_password
            else:
                print("Passwords do not match. Please try again.")
        else:
            print(
                "Invalid password. Password must be at least 8 characters long and contain at least one lowercase letter, one uppercase letter, and one digit. Please try again."
            )


def update_project_files_to_project_name(project_name):
    files = [
        "Dockerfile",
        "manage.py",
        "djazure/asgi.py",
        "djazure/urls.py",
        "djazure/wsgi.py",
        "djazure/settings/base.py",
    ]

    for filename in files:
        with fileinput.FileInput(filename, inplace=True) as file:
            for line in file:
                print(line.replace("djazure", project_name), end="")

    os.rename("djazure", project_name)


def login_to_azure():
    login = subprocess.run(
        ["az", "login"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if login.returncode != 0:
        raise CommandError(f"Error logging in to Azure: {login.stderr.decode()}")

    return login


def create_service_principal(project_name, subscription_id):
    create_service_principal = subprocess.run(
        [
            "az",
            "ad",
            "sp",
            "create-for-rbac",
            "--name",
            f"{project_name}-sp",
            "--role",
            "Contributor",
            "--scopes",
            f"/subscriptions/{subscription_id}",
            "--sdk-auth",
            "-o",
            "json",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if create_service_principal.returncode != 0:
        raise CommandError(
            f"Error creating Service Principal: {create_service_principal.stderr.decode()}"
        )

    return create_service_principal
