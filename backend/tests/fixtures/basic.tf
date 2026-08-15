# Formes HCL2 du pinning (docs/phase1/HCL2-PINNING.md) : valeurs brutes,
# blocs imbriqués, dynamic, heredoc, jsonencode, count/for_each.
resource "aws_s3_bucket" "this" {
  bucket        = var.bucket_name
  force_destroy = true
  tags          = var.tags
  count         = 2
}

resource "aws_iam_role" "r" {
  name = "role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow" }]
  })
}

resource "aws_x" "a" {
  policy = <<-EOT
    {"Version": "2012-10-17"}
  EOT
}

resource "aws_s3_bucket" "b" {
  versioning {
    status = "Enabled"
  }
}

resource "aws_x" "dyn" {
  dynamic "ingress" {
    for_each = var.ports
    content {
      port = ingress.value
    }
  }
}

resource "aws_x" "list" {
  methods = ["GET", "HEAD"]
}

resource "aws_x" "expr" {
  count = length(var.list)
}

resource "aws_x" "fe" {
  for_each = toset(var.items)
}
