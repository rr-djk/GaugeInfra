# Asymétrie required_providers : la clé provider (aws) n'est PAS quotée,
# contrairement aux labels. Deux blocs provider avec alias différents.
terraform {
  required_version = "1.15.8"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.58.0"
    }
  }
}

provider "aws" {
  region = var.region
}

provider "aws" {
  alias  = "west"
  region = "us-west-2"
}
