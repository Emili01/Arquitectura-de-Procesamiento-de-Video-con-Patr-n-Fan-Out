resource "aws_dynamodb_table" "video_metadata" {
  name           = "VideoMetadata"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "video_id"
  range_key      = "resolution"
  
  attribute {
    name = "video_id"
    type = "S"
  }
  
  attribute {
    name = "resolution"
    type = "S"
  }
  
  tags = {
    Environment = "localstack"
    Practice    = "practica2"
  }
}