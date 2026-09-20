config {
  module = true
  force = false
}

plugin "aws" {
  enabled = true
  version = "0.1.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}
