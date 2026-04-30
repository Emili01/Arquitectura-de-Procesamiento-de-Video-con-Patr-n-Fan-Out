terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  s3_use_path_style           = true 
  
  endpoints {
    s3         = "http://localhost:4566"
    dynamodb   = "http://localhost:4566"
    sns        = "http://localhost:4566"
    sqs        = "http://localhost:4566"
    lambda     = "http://localhost:4566"
    iam        = "http://localhost:4566"
    sts        = "http://localhost:4566"
  }
}


data "external" "localstack_ip" {
  program = ["bash", "-c", <<-EOF
    LOCALSTACK_NETWORK=$(docker inspect localstack --format='{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}' | awk '{print $1}')
    if [ -n "$LOCALSTACK_NETWORK" ]; then
      IP=$(docker inspect localstack --format="{{(index .NetworkSettings.Networks \"$LOCALSTACK_NETWORK\").IPAddress}}")
    fi
    if [ -z "$IP" ] || [ "$IP" = "invalid IP" ] || [ "$IP" = "<no value>" ]; then
      echo '{"ip": "localhost"}'
    else
      echo "{\"ip\": \"$IP\"}"
    fi
EOF
  ]
}

locals {
  localstack_ip = data.external.localstack_ip.result.ip
  resolutions   = ["720p", "480p"]
}
