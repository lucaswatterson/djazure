# Django on Azure Template

This template automates the deployment of a Django application to Azure through custom management commands, Terraform, and GitHub Actions.  The architecture diagram below details the resources deployed to Azure and the overall deployment flow.

![Django on Azure Architecture](./static/images/architecture.png)

1. A Visual Studio Code Devcontainer provides a fully-featured development environment and wraps all dependencies.

1. The custom `bootstrap` Django management command creates the required resources to remotely store Terraform state in Azure and creates secrets in the GitHub repository that enable the deployment and configuration of production resources by GitHub Actions.  The command only needs to be run once, directly after the repo is cloned.

1. Any push to `main` triggers a GitHub Action that manages Azure resources with Terraform, migrates the production database to an Azure SQL Database, collects the static files to a Storage Account, builds the production Docker image, and pushes that image to an Azure Container Registry.  On the initial push to `main`, Terraform creates and configures the required resources in Azure.  On sub-sequent pushes, Terraform manages any changes to the Azure resources made in [tf/main.tf](./tf/main.tf).

1. Secrets required by Azure resources and GitHub Actions are managed in an Azure Key Vault.

1. The continuous deployment capability in the App Service pulls the production container from the Azure Container Registry each time it is updated through the GitHub Action.

1. Static files are stored and served by an Azure Storage Account.

## Getting Started

## Terraform Variables

## Manual Dev Environment

## Contributing

## License∏