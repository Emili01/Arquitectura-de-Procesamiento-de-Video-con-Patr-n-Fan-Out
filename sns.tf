resource "aws_sns_topic" "video_processing" {
  name = "video-processing-topic"
  
  tags = {
    Environment = "localstack"
    Practice    = "practica2"
  }
}