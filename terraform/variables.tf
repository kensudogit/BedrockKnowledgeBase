variable "aws_region" {
  type    = string
  default = "ap-northeast-1"
}

variable "project" {
  type    = string
  default = "bkb"
}

variable "documents_bucket_name" {
  type = string
}

variable "lambda_zip_path" {
  type    = string
  default = "../lambda/dist/api.zip"
}

variable "bedrock_text_model_id" {
  type    = string
  default = "anthropic.claude-3-5-sonnet-20240620-v1:0"
}

variable "bedrock_embed_model_id" {
  type    = string
  default = "amazon.titan-embed-text-v2:0"
}

variable "bedrock_knowledge_base_id" {
  type    = string
  default = ""
}

variable "bedrock_guardrail_id" {
  type    = string
  default = ""
}

variable "bedrock_guardrail_version" {
  type    = string
  default = "DRAFT"
}
