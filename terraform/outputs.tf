output "cognito_user_pool_id" {
  description = "Cognito User Pool ID（API の COGNITO_USER_POOL_ID）"
  value       = var.enable_cognito ? aws_cognito_user_pool.main[0].id : ""
}

output "cognito_app_client_id" {
  description = "SPA App Client ID（フロント / API の COGNITO_APP_CLIENT_ID）"
  value       = var.enable_cognito ? aws_cognito_user_pool_client.spa[0].id : ""
}

output "cognito_hosted_ui_base_url" {
  description = "Hosted UI ベース URL（ログインリダイレクト用）"
  value = var.enable_cognito ? format(
    "https://%s.auth.%s.amazoncognito.com",
    aws_cognito_user_pool_domain.main[0].domain,
    var.aws_region,
  ) : ""
}

output "cognito_domain_prefix" {
  value = var.enable_cognito ? aws_cognito_user_pool_domain.main[0].domain : ""
}

output "cognito_oauth_authorize_url_hint" {
  description = "ブラウザログイン URL の例（redirect_uri は環境に合わせる）"
  value = var.enable_cognito && length(var.cognito_callback_urls) > 0 ? format(
    "%s/oauth2/authorize?client_id=%s&response_type=code&scope=openid+email+profile&redirect_uri=%s",
    "https://${aws_cognito_user_pool_domain.main[0].domain}.auth.${var.aws_region}.amazoncognito.com",
    aws_cognito_user_pool_client.spa[0].id,
    var.cognito_callback_urls[0],
  ) : ""
}
