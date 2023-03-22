import os
import subprocess
import json
from datetime import datetime
import fileinput
import getpass
import re

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Bootstrap a Project from the Django on Azure Template"

    def handle(self, *args, **options):
        # Get, Validate, and Transform User Input

        project_name = get_project_name()
        print()
        subscription_id = get_subscription_id()
        print()
        region = get_azure_region()
        print()
        superuser_user = get_superuser_username()
        print()
        superuser_password = get_superuser_password()
        unique_id = datetime.now().strftime("%Y%m%d%H%M%S")
        print()

        # Update Project Files to Project Name
        print("Updating Project Files to Project Name")
        update_project_files_to_project_name(project_name)
        print()

        # Login to Azure
        print("Logging in to Azure")
        login_to_azure()
        print()

        # Check if a Resource Group with the Project Name Already Exists and Prompt the User
        cmd = f"az group list --query \"[?contains(name, '{project_name}')].name\" -o tsv"
        rg_list_output = subprocess.check_output(cmd, shell=True, text=True)
        rg_list_output.strip().replace("\n", "")

        if rg_list_output:
            print()
            decision = input(
                f"A Resource Group named {rg_list_output} already exists.  Allowing this bootstrap to finish may cause new Azure resources to be created.  Are you sure you want to continue? (y/n) "
            )
            decision.lower().strip().replace("\n", "")

            if decision == "n":
                return

        # Create a Service Principal
        print("Creating Service Principal")
        service_principal = create_service_principal(project_name, subscription_id)

        # Parse the Service Principal JSON
        credentials = service_principal.stdout.decode("utf-8").strip().replace("\n", "")
        auth_info = json.loads(credentials)

        print()

        # Create Resource Group, Storage Account, and Container for TF Satet
        print("Creating Resources to Store Terraform State")

        set_azure_subscription(subscription_id)
        resource_group_name = create_resource_group(project_name, region)
        storage_account_name = create_storage_account(
            project_name, unique_id, resource_group_name, region
        )
        create_container(storage_account_name)
        print()

        # Set GitHub Secrets
        print("Logging in to GitHub")
        print()
        os.system("gh auth login")
        print()
        print("Setting GitHub Secrets")
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

        add_azure_credentials_github = subprocess.run(
            ["gh", "secret", "set", "-f", ".env"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if add_azure_credentials_github.returncode != 0:
            raise CommandError(
                f"Error adding secrets to GitHub: {add_azure_credentials_github.stderr.decode()}"
            )

        print()

        print(f"{project_name} has been bootstrapped with the Django on Azure Template!")
        print()
        print(f"Commit the changes to your GitHub repo to trigger the GitHub Action.")


def get_project_name():
    project_name = input("What is the name of your project? (djazure) ") or "djazure"

    if re.match("^[a-z]*$", project_name):
        return project_name

    project_name = re.sub("[^a-z]+", "", project_name)
    project_name = project_name.lower().replace("\n", "")

    return project_name


def get_subscription_id():
    subscription_id = ""

    while subscription_id == "":
        subscription_id = input("What is your Azure Subscription ID? ")

    subscription_id = subscription_id.strip().replace("\n", "")

    return subscription_id


def get_azure_region():
    region = input("Which Azure Region do you want to deploy to? (eastus) ") or "eastus"

    region = region.lower().strip().replace("\n", "")

    return region


def get_superuser_username():
    while True:
        superuser_user = (
            input("What do you want the Superuser's username to be? (admin) ") or "admin"
        )
        superuser_user = superuser_user.lower().strip().replace("\n", "")

        if re.match("^[a-zA-Z_][a-zA-Z0-9_]*$", superuser_user):
            return superuser_user
        else:
            print(
                "Invalid username. Username must be a valid identifier according to Python naming conventions (i.e. can only contain letters, numbers, and underscores, and cannot start with a number). Please try again."
            )


def get_superuser_password():
    while True:
        superuser_password = getpass.getpass("What do you want the Superuser's password to be? ")
        print()
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
    service_principal = subprocess.run(
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

    if service_principal.returncode != 0:
        raise CommandError(f"Error creating Service Principal: {service_principal.stderr.decode()}")

    return service_principal


def set_azure_subscription(subscription_id):
    set_subscription = subprocess.run(
        ["az", "account", "set", "--subscription", f"{subscription_id}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if set_subscription.returncode != 0:
        raise CommandError(f"Error setting Subscription: {set_subscription.stderr.decode()}")


def create_resource_group(project_name, region):
    resource_group_name = f"{project_name}-tf-state-rg"
    resource_group = subprocess.run(
        ["az", "group", "create", "-l", f"{region}", "-n", resource_group_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if resource_group.returncode != 0:
        raise CommandError(f"Error creating Resource Group: {resource_group.stderr.decode()}")

    return resource_group_name


def create_storage_account(project_name, unique_id, resource_group_name, region):
    storage_account_name = f"{project_name}storage{unique_id}"[:24]
    storage_account = subprocess.run(
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

    if storage_account.returncode != 0:
        raise CommandError(f"Error creating Storage Account: {storage_account.stderr.decode()}")

    return storage_account_name


def create_container(storage_account_name):
    container = subprocess.run(
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

    if container.returncode != 0:
        raise CommandError(f"Error creating Container: {container.stderr.decode()}")
