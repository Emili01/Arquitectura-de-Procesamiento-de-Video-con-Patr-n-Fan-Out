resource "aws_s3_bucket" "raw_videos" {
  bucket = "bucket-a-raw"
  force_destroy = true
}

resource "aws_s3_bucket" "processed_videos" {
  bucket = "bucket-b-processed"
  force_destroy = true
}

resource "aws_s3_bucket_notification" "raw_bucket_notification" {
  bucket = aws_s3_bucket.raw_videos.id

  topic {
    topic_arn     = aws_sns_topic.video_processing.arn
    events        = ["s3:ObjectCreated:*"]
  }
  depends_on = [aws_sns_topic_policy.allow_s3_publish] 
}

resource "aws_sns_topic_policy" "allow_s3_publish" {
  arn    = aws_sns_topic.video_processing.arn
  policy = data.aws_iam_policy_document.sns_topic_policy.json
}

data "aws_iam_policy_document" "sns_topic_policy" {
  statement {
    effect  = "Allow"
    actions = ["SNS:Publish"]
    
    principals {
      type        = "Service"
      identifiers = ["s3.amazonaws.com"]
    }
    
    resources = [aws_sns_topic.video_processing.arn]
    
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = [aws_s3_bucket.raw_videos.arn]
    }
  }
}
