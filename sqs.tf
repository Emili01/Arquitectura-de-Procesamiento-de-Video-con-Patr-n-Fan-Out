resource "aws_sqs_queue" "dlq" {
  for_each = toset(local.resolutions)
  name     = "video-processing-dlq-${each.key}"
  
  tags = {
    Environment = "localstack"
    Purpose     = "dead-letter-queue"
    Resolution  = each.key
  }
}

resource "aws_sqs_queue" "processing_queues" {
  for_each = toset(local.resolutions)
  name     = "video-processing-queue-${each.key}"
  
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = var.dlq_max_receive_count
  })
  
  tags = {
    Environment = "localstack"
    Purpose     = "processing-queue"
    Resolution  = each.key
  }
}

# Suscripción SQS -> SNS
resource "aws_sns_topic_subscription" "sqs_subscriptions" {
  for_each  = toset(local.resolutions)
  topic_arn = aws_sns_topic.video_processing.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.processing_queues[each.key].arn
  
  depends_on = [aws_sqs_queue_policy.queue_policy]
}

resource "aws_sqs_queue_policy" "queue_policy" {
  for_each  = toset(local.resolutions)
  queue_url = aws_sqs_queue.processing_queues[each.key].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.processing_queues[each.key].arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_sns_topic.video_processing.arn
          }
        }
      },
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.processing_queues[each.key].arn
      }
    ]
  })
}
