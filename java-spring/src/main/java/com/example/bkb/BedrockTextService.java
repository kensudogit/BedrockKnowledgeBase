package com.example.bkb;

/**
 * Spring Boot から Amazon Bedrock Runtime を呼ぶためのスケルトン。
 * 実プロジェクトでは AWS SDK for Java v2 の BedrockRuntimeClient を注入してください。
 */
public class BedrockTextService {

  private final String modelId;
  private final String region;

  public BedrockTextService(String modelId, String region) {
    this.modelId = modelId;
    this.region = region;
  }

  /**
   * @param prompt ユーザー入力
   * @return モデル応答テキスト（未接続時はプレースホルダ）
   */
  public String generate(String prompt) {
    // TODO: BedrockRuntimeClient.invokeModel(modelId, body)
    return "[stub] Bedrock Runtime call is not wired. region="
        + region
        + " model="
        + modelId
        + " prompt="
        + prompt;
  }
}
