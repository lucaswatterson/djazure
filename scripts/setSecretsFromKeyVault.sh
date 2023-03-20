#!/bin/bash

# Get the resource group name from the environment variable
resource_group_name=$RESOURCE_GROUP_NAME

# Get the Key Vault name
kv_list=$(az keyvault list --resource-group $resource_group_name)
kv_name=$(echo $kv_list | jq -r '.[0].name')

# Get the secrets from the Key Vault
secrets=$(az keyvault secret list --vault-name $kv_name | jq -c '.[]')

# Map the secrets to environment variables
declare -A secret_mapping=(
  ["acr-password"]="REGISTRY_PASSWORD"
  ["acr-server"]="REGISTRY_SERVER"
  ["acr-user"]="REGISTRY_USERNAME"
  ["blob-connection-string"]="BLOB_CONNECTION_STRING"
  ["db-fqdn"]="DB_FQDN"
  ["db-name"]="DB_NAME"
  ["db-password"]="DB_PASSWORD"
  ["db-server"]="DB_SERVER"
  ["db-user"]="DB_USER"
  ["hostname"]="HOSTNAME"
  ["secret-key"]="SECRET_KEY"
)

# Set the environment variables in the GitHub environment file
for secret in $secrets; do
  # Get the name and value of the secret
  secret_name=$(echo $secret | jq -r '.name')
  secret_value=$(az keyvault secret show --vault-name $kv_name --name $secret_name --query 'value' | tr -d '"')

  # Get the environment variable name from the mapping
  env_var=${secret_mapping[$secret_name]}

  # Echo the environment variable in the GitHub environment file
  echo "$env_var=$secret_value" >> $GITHUB_ENV
done