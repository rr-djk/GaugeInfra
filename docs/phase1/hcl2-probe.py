import hcl2

SNIPPETS = {
    "labels": 'resource "aws_s3_bucket" "this" {\n  bucket = var.bucket_name\n}\n',
    "count_int": 'resource "aws_x" "a" {\n  count = 2\n}\n',
    "count_expr": 'resource "aws_x" "a" {\n  count = length(var.list)\n}\n',
    "for_each": 'resource "aws_x" "a" {\n  for_each = toset(var.items)\n}\n',
    "jsonencode": (
        'resource "aws_iam_role" "r" {\n'
        "  assume_role_policy = jsonencode({\n"
        '    Version = "2012-10-17"\n'
        '    Statement = [{ Effect = "Allow" }]\n'
        "  })\n"
        "}\n"
    ),
    "heredoc": (
        'resource "aws_x" "a" {\n'
        "  policy = <<-EOT\n"
        '    {"Version": "2012-10-17"}\n'
        "  EOT\n"
        "}\n"
    ),
    "nested": (
        'resource "aws_s3_bucket" "b" {\n'
        "  versioning {\n"
        '    status = "Enabled"\n'
        "  }\n"
        "}\n"
    ),
    "dynamic": (
        'resource "aws_x" "a" {\n'
        '  dynamic "ingress" {\n'
        "    for_each = var.ports\n"
        "    content {\n"
        "      port = ingress.value\n"
        "    }\n"
        "  }\n"
        "}\n"
    ),
    "backend": (
        "terraform {\n"
        '  backend "s3" {\n'
        '    bucket = "x"\n'
        "    use_lockfile = true\n"
        "  }\n"
        "}\n"
    ),
    "providers": (
        "terraform {\n"
        "  required_providers {\n"
        "    aws = {\n"
        '      source  = "hashicorp/aws"\n'
        '      version = "6.58.0"\n'
        "    }\n"
        "  }\n"
        "}\n"
    ),
    "ref": 'resource "aws_x" "a" {\n  bucket = aws_s3_bucket.this.id\n}\n',
    "list": 'resource "aws_x" "a" {\n  methods = ["GET", "HEAD"]\n}\n',
}

for name, src in SNIPPETS.items():
    print(f"=== {name} ===")
    try:
        parsed = hcl2.loads(src)
        print(repr(parsed))
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
    print()

print("=== invalid hcl ===")
try:
    hcl2.loads('resource "aws_x" "a" {\n  bucket = \n}\n')
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

print("\n=== tf.json ===")
try:
    hcl2.loads('{"resource": {}}')
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

print("\n=== empty ===")
print(repr(hcl2.loads("")))
