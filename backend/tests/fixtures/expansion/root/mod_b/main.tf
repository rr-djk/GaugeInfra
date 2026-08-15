module "c" {
  source = "../mod_c"
}

resource "aws_s3_bucket" "b_bucket" {
  bucket = "b"
}
