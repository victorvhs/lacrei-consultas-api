terraform {
  required_version = ">= 1.9.0"

  backend "s3" {
    bucket = "lacrei-terraform-state"
    key    = "production/terraform.tfstate"
    region = "sa-east-1"
  }
}

variable "environment" {
  default = "production"
}
