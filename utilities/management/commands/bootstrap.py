import os
import subprocess
import json
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a service principal in Azure"

    def handle(self, *args, **options):
        # Get User Input
        project_name = input("What is the name of your project? (djazure) ") or "djazure"
        project_name.lower()

        subscription_id = ""
        while subscription_id == "":
            subscription_id = input("\nWhat is your Azure Subscription ID? ")

        region = input("\nWhich Azure Region do you want to deploy to? (eastus) ") or "eastus"
        region.lower()

        unique_id = datetime.now().strftime("%Y%m%d%H%M%S")

        # Login to Azure
        print("\nLogging in to Azure")

        login = subprocess.run(
            ["az", "login"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if login.returncode != 0:
            raise CommandError(f"Error logging in to Azure: {login.stderr.decode()}")

        # Create a Service Principal
        print("\nCreating Service Principal")
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
