# NOTE: every resource here is created on a LOCAL AWS EMULATOR (LocalStack),
# not on real AWS. See docs/adr and infra/README.md for why.

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test" # dummy credentials for LocalStack
  secret_key                  = "test"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3  = "http://localhost:4566"
    sns = "http://localhost:4566"
  }
}

locals {
  tags = {
    project     = "healthqueue"
    managed_by  = "opentofu"
    environment = "local-emulator"
    team        = "platform"
  }
}

# Cloud resource 1: archive for supply chain evidence (SBOMs, scan reports).
resource "aws_s3_bucket" "supply_chain_artifacts" {
  bucket = "healthqueue-supply-chain-artifacts"
  tags   = local.tags
}

# Keep old versions so an overwritten or deleted report can be recovered.
resource "aws_s3_bucket_versioning" "supply_chain_artifacts" {
  bucket = aws_s3_bucket.supply_chain_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Cloud resource 2: destination for operational alerts (see the observability plan).
resource "aws_sns_topic" "alerts" {
  name = "healthqueue-alerts"
  tags = local.tags
}
