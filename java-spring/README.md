# Spring Boot + Bedrock Runtime API（連携スタブ）

Java 業務システムから Bedrock を呼ぶ場合の配置例です。

## 想定依存

```xml
<dependency>
  <groupId>software.amazon.awssdk</groupId>
  <artifactId>bedrockruntime</artifactId>
</dependency>
```

## 呼び出しイメージ

`BedrockRuntimeClient.invokeModel(...)` で Claude / Titan を実行し、
既存の Spring Service から社内 API として公開します。

本リポジトリの主系統は **Python FastAPI + Next.js** です。
Java 側は既存基幹への組込み用アダプタとして拡張してください。
