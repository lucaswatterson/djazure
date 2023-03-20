#!/bin/bash

# Get the resource group name from the environment variable
resource_group_name=$RESOURCE_GROUP_NAME

# Get the web app name
web_app_list=$(az webapp list --resource-group $resource_group_name)
web_app_name=$(echo $web_app_list | jq -r '.[0].name')

# Set the CI/CD Flag
az webapp deployment container config \
    --enable-cd true \
    --name $web_app_name \
    --resource-group $resource_group_name