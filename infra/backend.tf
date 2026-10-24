terraform {
  required_version = ">= 1.10.0" # native S3 state locking (use_lockfile) needs OpenTofu 1.10+

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state in an S3 bucket on the LocalStack emulator.
  # The bucket must exist before `tofu init` (see infra/README.md, step 2).
  # Backend blocks cannot use variables, so the values are written out.
  backend "s3" {
    bucket = "healthqueue-tofu-state"
    key    = "patient-scheduling/terraform.tfstate"
    region = "us-east-1"

    endpoints = {
      s3 = "http://localhost:4566"
    }
    use_path_style              = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_requesting_account_id  = true
    skip_region_validation      = true

    # Dummy credentials: LocalStack accepts any value. These are not real secrets.
    access_key = "test"
    secret_key = "test"

    # State locking through an S3 lock file (conditional writes), no DynamoDB table.
    use_lockfile = true
  }
}
