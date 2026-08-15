module "b" {
  source = "../mod_b"
}

resource "aws_s3_bucket" "a_bucket" {
  bucket = "a"
}
