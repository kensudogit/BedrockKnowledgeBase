# Amazon Cognito User Pool（SPA + Authorization Code PKCE）
# アクセストークンを FastAPI が検証（ID トークンは API 認証に使わない）

resource "aws_cognito_user_pool" "main" {
  count = var.enable_cognito ? 1 : 0
  name  = "${var.project}-users"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  schema {
    name                     = "tenant_id"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = false
    string_attribute_constraints {
      min_length = 1
      max_length = 128
    }
  }

  user_attribute_update_settings {
    attributes_require_verification_before_update = ["email"]
  }

  tags = {
    Project = var.project
    Module  = "cognito"
  }
}

resource "aws_cognito_user_pool_domain" "main" {
  count        = var.enable_cognito ? 1 : 0
  domain       = local.cognito_domain
  user_pool_id = aws_cognito_user_pool.main[0].id
}

resource "aws_cognito_user_pool_client" "spa" {
  count        = var.enable_cognito ? 1 : 0
  name         = "${var.project}-spa"
  user_pool_id = aws_cognito_user_pool.main[0].id

  generate_secret                      = false
  prevent_user_existence_errors        = "ENABLED"
  enable_token_revocation              = true
  supported_identity_providers         = ["COGNITO"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  callback_urls                        = var.cognito_callback_urls
  logout_urls                          = var.cognito_logout_urls

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
  ]

  access_token_validity  = 60
  id_token_validity      = 60
  refresh_token_validity = 30
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  read_attributes  = ["email", "custom:tenant_id"]
  write_attributes = ["email", "custom:tenant_id"]
}

resource "aws_cognito_user_pool_group" "admin" {
  count        = var.enable_cognito ? 1 : 0
  name         = "admin"
  user_pool_id = aws_cognito_user_pool.main[0].id
  description  = "Tenant administrators"
  precedence   = 1
}

resource "aws_cognito_user_pool_group" "editor" {
  count        = var.enable_cognito ? 1 : 0
  name         = "editor"
  user_pool_id = aws_cognito_user_pool.main[0].id
  description  = "Document editors"
  precedence   = 10
}

resource "aws_cognito_user_pool_group" "viewer" {
  count        = var.enable_cognito ? 1 : 0
  name         = "viewer"
  user_pool_id = aws_cognito_user_pool.main[0].id
  description  = "Read-only users"
  precedence   = 20
}
