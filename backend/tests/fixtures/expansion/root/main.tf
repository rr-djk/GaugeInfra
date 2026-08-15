# Racine d'expansion : module local imbriqué (a -> b -> c), source distante
# (jamais une erreur) et module local introuvable (collecté, jamais levé).
module "a" {
  source = "./mod_a"
}

module "remote" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
}

module "missing" {
  source = "./mod_missing"
}

resource "aws_s3_bucket" "root_bucket" {
  bucket = "root"
}
