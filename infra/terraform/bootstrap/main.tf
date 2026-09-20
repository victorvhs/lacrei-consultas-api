terraform {
  required_version = ">= 1.9.0"

  backend "s3" {
    bucket = "lacrei-terraform-state"
    key    = "bootstrap/terraform.tfstate"
    region = "sa-east-1"
  }
}
