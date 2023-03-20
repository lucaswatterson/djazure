// Configure TF.

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "3.48.0"
    }
  }

  backend "azurerm" {
    container_name = "state"
    key            = "terraform.tfstate"
  }

  required_version = ">= 1.1.0"
}

provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {}

// Create random strings for resource names and SQL authentication.

resource "random_string" "unique_resource_string" {
  length  = 5
  special = false
  upper   = false
}

resource "random_string" "secret_key" {
  length           = 50
  special          = true
  override_special = "!@#$%^&*(-_=+)"
}

resource "random_string" "sql_username" {
  length  = 16
  special = false
  upper   = false
}

resource "random_password" "sql_password" {
  length           = 55
  special          = true
  override_special = "!$#%"
}

// Create a Resource Group.

resource "azurerm_resource_group" "rg" {
  name     = var.project_name
  location = var.region
}

// Create an Azure Key Vault.

resource "azurerm_key_vault" "key_vault" {
  name                = join("", [var.project_name, "-akv-", random_string.unique_resource_string.id])
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"
}

resource "azurerm_key_vault_access_policy" "tf_access_policy" {
  key_vault_id = azurerm_key_vault.key_vault.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Set",
    "Get",
    "List",
    "Delete",
    "Purge",
    "Recover",
    "Backup",
    "Restore"
  ]
}

resource "azurerm_key_vault_secret" "secret_key" {
  name         = "secret-key"
  value        = random_string.secret_key.id
  key_vault_id = azurerm_key_vault.key_vault.id

  depends_on = [
    azurerm_key_vault_access_policy.tf_access_policy
  ]
}

// Create a Storage Account.

resource "azurerm_storage_account" "storage_account" {
  name                     = join("", [var.project_name, "storage", random_string.unique_resource_string.id])
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  blob_properties {
    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["GET"]
      allowed_origins    = [join("", ["https://", azurerm_linux_web_app.web_app.default_hostname])]
      exposed_headers    = ["*"]
      max_age_in_seconds = 0
    }
  }
}

resource "azurerm_storage_container" "container" {
  name                  = "files"
  storage_account_name  = azurerm_storage_account.storage_account.name
  container_access_type = "blob"
}

resource "azurerm_key_vault_secret" "blob_connection_string" {
  name         = "blob-connection-string"
  value        = azurerm_storage_account.storage_account.primary_blob_connection_string
  key_vault_id = azurerm_key_vault.key_vault.id

  depends_on = [
    azurerm_key_vault_access_policy.tf_access_policy
  ]
}

// Create a Container Registry.

resource "azurerm_container_registry" "acr" {
  name                = join("", [var.project_name, "acr", random_string.unique_resource_string.id])
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
}

resource "azurerm_key_vault_secret" "acr_server" {
  name         = "acr-server"
  value        = azurerm_container_registry.acr.login_server
  key_vault_id = azurerm_key_vault.key_vault.id

  depends_on = [
    azurerm_key_vault_access_policy.tf_access_policy
  ]
}

resource "azurerm_key_vault_secret" "acr_user" {
  name         = "acr-user"
  value        = azurerm_container_registry.acr.admin_username
  key_vault_id = azurerm_key_vault.key_vault.id

  depends_on = [
    azurerm_key_vault_access_policy.tf_access_policy
  ]
}

resource "azurerm_key_vault_secret" "acr_password" {
  name         = "acr-password"
  value        = azurerm_container_registry.acr.admin_password
  key_vault_id = azurerm_key_vault.key_vault.id

  depends_on = [
    azurerm_key_vault_access_policy.tf_access_policy
  ]
}

// Create a SQL Server.

resource "azurerm_mssql_server" "sql_server" {
  name                         = join("", [var.project_name, "sqlserver", random_string.unique_resource_string.id])
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = azurerm_resource_group.rg.location
  version                      = "12.0"
  administrator_login          = random_string.sql_username.id
  administrator_login_password = random_password.sql_password.result
}

resource "azurerm_mssql_firewall_rule" "allow_azure_resources" {
  name             = "AllowAllAzure"
  server_id        = azurerm_mssql_server.sql_server.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_key_vault_secret" "db_fqdn" {
  name         = "db-fqdn"
  value        = azurerm_mssql_server.sql_server.fully_qualified_domain_name
  key_vault_id = azurerm_key_vault.key_vault.id

  depends_on = [
    azurerm_key_vault_access_policy.tf_access_policy
  ]
}

resource "azurerm_key_vault_secret" "db_server" {
  name         = "db-server"
  value        = azurerm_mssql_server.sql_server.name
  key_vault_id = azurerm_key_vault.key_vault.id

  depends_on = [
    azurerm_key_vault_access_policy.tf_access_policy
  ]
}

resource "azurerm_key_vault_secret" "db_user" {
  name         = "db-user"
  value        = azurerm_mssql_server.sql_server.administrator_login
  key_vault_id = azurerm_key_vault.key_vault.id

  depends_on = [
    azurerm_key_vault_access_policy.tf_access_policy
  ]
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  value        = azurerm_mssql_server.sql_server.administrator_login_password
  key_vault_id = azurerm_key_vault.key_vault.id

  depends_on = [
    azurerm_key_vault_access_policy.tf_access_policy
  ]
}

// Create a SQL Database.

resource "azurerm_mssql_database" "sql_database" {
  name         = join("", [var.project_name, "sqldatabase", random_string.unique_resource_string.id])
  server_id    = azurerm_mssql_server.sql_server.id
  license_type = "LicenseIncluded"
  sku_name     = "Basic"
}

resource "azurerm_key_vault_secret" "db_name" {
  name         = "db-name"
  value        = azurerm_mssql_database.sql_database.name
  key_vault_id = azurerm_key_vault.key_vault.id

  depends_on = [
    azurerm_key_vault_access_policy.tf_access_policy
  ]
}

// Create a Linux App Service Plan.

resource "azurerm_service_plan" "app_service_plan" {
  name                = join("", [var.project_name, "serviceplan", random_string.unique_resource_string.id])
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "B1"
}

// Create a Linux Web App.

resource "azurerm_linux_web_app" "web_app" {
  name                = join("", [var.project_name, random_string.unique_resource_string.id])
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_service_plan.app_service_plan.location
  service_plan_id     = azurerm_service_plan.app_service_plan.id

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      docker_image     = "${azurerm_container_registry.acr.login_server}/${var.project_name}"
      docker_image_tag = "latest"
    }
  }

  app_settings = {
    WEBSITES_PORT                   = "8000"
    DOCKER_ENABLE_CI                = "true"
    DOCKER_REGISTRY_SERVER_URL      = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.key_vault.name};SecretName=acr-server)"
    DOCKER_REGISTRY_SERVER_USERNAME = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.key_vault.name};SecretName=acr-user)"
    DOCKER_REGISTRY_SERVER_PASSWORD = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.key_vault.name};SecretName=acr-password)"
    BLOB_CONNECTION_STRING          = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.key_vault.name};SecretName=blob-connection-string)"
    DB_FQDN                         = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.key_vault.name};SecretName=db-fqdn)"
    DB_SERVER                       = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.key_vault.name};SecretName=db-server)"
    DB_USER                         = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.key_vault.name};SecretName=db-user)"
    DB_PASSWORD                     = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.key_vault.name};SecretName=db-password)"
    DB_NAME                         = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.key_vault.name};SecretName=db-name)"
    HOSTNAME                        = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.key_vault.name};SecretName=hostname)"
    SECRET_KEY                      = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.key_vault.name};SecretName=secret-key)"
  }
}

resource "azurerm_key_vault_secret" "hostname" {
  name         = "hostname"
  value        = azurerm_linux_web_app.web_app.default_hostname
  key_vault_id = azurerm_key_vault.key_vault.id

  depends_on = [
    azurerm_key_vault_access_policy.tf_access_policy
  ]
}

// Create a Key Vault Access Policy for the Linux Web App.

resource "azurerm_key_vault_access_policy" "app_access_policy" {
  key_vault_id = azurerm_key_vault.key_vault.id
  tenant_id    = azurerm_linux_web_app.web_app.identity.0.tenant_id
  object_id    = azurerm_linux_web_app.web_app.identity.0.principal_id

  secret_permissions = [
    "Set",
    "Get",
    "List",
    "Delete",
    "Purge",
    "Recover",
    "Backup",
    "Restore"
  ]
}
