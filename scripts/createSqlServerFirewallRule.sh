#!/bin/bash

# Get the resource group name from the environment variable
resource_group_name=$RESOURCE_GROUP_NAME

# Get the SQL server name
sql_server_list=$(az sql server list --resource-group $resource_group_name)
sql_server_name=$(echo $sql_server_list | jq -r '.[0].name')

# Get the client IP address
client_ip_address=$(hostname -I | awk '{print $1}')

# Create the firewall rule
az sql server firewall-rule create \
    --name AllowGitHubAction \
    --resource-group $resource_group_name \
    --server $sql_server_name \
    --start-ip-address $client_ip_address \
    --end-ip-address $client_ip_address