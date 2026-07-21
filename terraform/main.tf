terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "documents" {
  bucket = var.documents_bucket_name
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_dynamodb_table" "prompts" {
  name         = "${var.project}-prompts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "prompt_id"
  attribute {
    name = "prompt_id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "evals" {
  name         = "${var.project}-evals"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "eval_id"
  attribute {
    name = "eval_id"
    type = "S"
  }
}

resource "aws_iam_role" "lambda" {
  name = "${var.project}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_bedrock" {
  name = "${var.project}-bedrock-access"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:ApplyGuardrail",
          "bedrock:Retrieve",
          "bedrock:RetrieveAndGenerate",
          "bedrock:InvokeAgent"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket", "s3:PutObject"]
        Resource = [aws_s3_bucket.documents.arn, "${aws_s3_bucket.documents.arn}/*"]
      },
      {
        Effect = "Allow"
        Action = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Scan", "dynamodb:Query"]
        Resource = [
          aws_dynamodb_table.prompts.arn,
          aws_dynamodb_table.evals.arn
        ]
      }
    ]
  })
}

# Knowledge Base / OpenSearch Serverless はアカウント依存のため、
# 実 ID は変数で受け取り、Lambda 環境変数へ注入する想定です。
resource "aws_lambda_function" "api" {
  function_name = "${var.project}-api"
  role          = aws_iam_role.lambda.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  filename      = var.lambda_zip_path
  timeout       = 60
  memory_size   = 1024

  environment {
    variables = {
      BEDROCK_TEXT_MODEL_ID      = var.bedrock_text_model_id
      BEDROCK_EMBED_MODEL_ID     = var.bedrock_embed_model_id
      BEDROCK_KNOWLEDGE_BASE_ID  = var.bedrock_knowledge_base_id
      BEDROCK_GUARDRAIL_ID       = var.bedrock_guardrail_id
      BEDROCK_GUARDRAIL_VERSION  = var.bedrock_guardrail_version
      S3_DOCUMENTS_BUCKET        = aws_s3_bucket.documents.bucket
      DYNAMODB_TABLE_PROMPTS     = aws_dynamodb_table.prompts.name
      DYNAMODB_TABLE_EVALS       = aws_dynamodb_table.evals.name
      USE_BEDROCK_MOCK           = "false"
    }
  }
}

resource "aws_apigatewayv2_api" "http" {
  name          = "${var.project}-http"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

output "api_endpoint" {
  value = aws_apigatewayv2_api.http.api_endpoint
}

output "documents_bucket" {
  value = aws_s3_bucket.documents.bucket
}
