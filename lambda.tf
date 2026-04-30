data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_function.py"
  output_path = "${path.module}/function.zip"
}

resource "aws_lambda_function" "video_processor" {
  for_each      = toset(local.resolutions)
  function_name = "VideoProcessor-${each.key}"
  
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  
  runtime  = "python3.9"
  handler  = "lambda_function.lambda_handler"
  role     = aws_iam_role.lambda_role.arn
  timeout  = var.lambda_timeout
  memory_size = var.lambda_memory_size
  
  environment {
    variables = {
      TARGET_RESOLUTION   = each.key
      LOCALSTACK_HOSTNAME = local.localstack_ip
    }
  }
  
  depends_on = [aws_iam_role_policy.lambda_policy]
}

# Event Source Mapping: SQS -> Lambda
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  for_each         = toset(local.resolutions)
  event_source_arn = aws_sqs_queue.processing_queues[each.key].arn
  function_name    = aws_lambda_function.video_processor[each.key].arn
  
  batch_size       = 1
  enabled          = true
  
depends_on = [aws_sqs_queue_policy.queue_policy] 
}
