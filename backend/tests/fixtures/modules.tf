# Appels de modules : source distante (jamais une erreur) et source locale
# (non résolue en paste mode — parse_files n'expand pas).
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
  name    = var.name
}

module "local" {
  source = "./local_mod"
  count  = 3
}
