output "supply_chain_artifacts_bucket" {
  description = "Bucket that stores SBOMs and scan reports."
  value       = aws_s3_bucket.supply_chain_artifacts.bucket
}

output "alerts_topic_arn" {
  description = "SNS topic that receives operational alerts."
  value       = aws_sns_topic.alerts.arn
}
