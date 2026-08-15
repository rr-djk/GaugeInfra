# Blocs inconnus (moved, import, check) : comptés dans other_blocks,
# jamais ignorés silencieusement.
moved {
  from = aws_s3_bucket.a
  to   = aws_s3_bucket.b
}

import {
  to = aws_s3_bucket.this
  id = "bucket-name"
}

check "health" {
  data "http" "x" {
    url = "https://example.com"
  }
}
