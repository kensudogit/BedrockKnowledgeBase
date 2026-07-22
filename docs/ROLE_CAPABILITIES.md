# 業務内容 ↔ プラットフォーム対応

## 1. AIモデルの分析・開発

| 業務 | 機能 | 入口 |
|---|---|---|
| 生成AI・自然言語 | Text 生成、Embedding、実験記録 | `/lab` Text · `/api/analysis/text` |
| 画像 | Image Generation + experiment | `/lab` Image · `/api/analysis/image` |
| 文書/RAG | ハイブリッド RAG 分析 | `/lab` RAG · `/chat` |
| テーブルデータ | プロファイル・相関・Ridge ベースライン学習 | `/lab` Tabular · `/api/analysis/tabular` |
| 実験管理 | modality / metrics / artifacts | `/api/experiments` |

## 2. 機械学習モデルのプロダクション化

| 業務 | 機能 | 入口 |
|---|---|---|
| モデル登録 | Model Registry | `POST /api/models` · Lab「レジストリ登録」 |
| 環境昇格 | development → staging → production | `/ops` 昇格ボタン · `POST /api/models/{id}/promote` |
| ランタイムピン | modality 別 active model | `GET /api/models` → `active` |
| Bedrock 統合 | KB / Guardrails / Agents / S3 ingest | env + Terraform + `/documents` KB取込 |
| 品質ゲート | eval fail-under（CI） | `python -m src.scripts.run_eval --fail-under` |

## 3. AIアプリケーションの構築と運用

| 業務 | 機能 | 入口 |
|---|---|---|
| アプリ構築 | Chat / Documents / Agents / Prompts UI + API | Next.js + FastAPI |
| 継続デリバリー | GitHub Actions CI（pytest + eval + build） | `.github/workflows/ci.yml` |
| 精度モニタリング | snapshot / alerts / feedback | `/ops` · `/api/monitoring/*` |
| 利用観測 | latency / error / mock rate | `/api/metrics/summary` |
| 新手法の探索 | Lab + datasets 拡張 + 実験比較 | `/lab` · `/evaluation` · DS_WORKFLOW.md |
| GCP 連携 | Vertex AI テキスト / GCS アップロード | `/gcp` · `/api/gcp/*` |
| 信用情報管理 | 本人・契約・同意・照会・スコア・監査 | `/credit` · `/api/credit/*` |

## 推奨フロー（受託 / 自社共通）

1. **Lab** で modality 別に分析・実験
2. **Evaluation / Datasets** で精度を数値化
3. **Model Registry** に登録し staging → production へ昇格
4. **Ops** で delivery readiness・アラート・フィードバックを監視
5. 改善ループ: feedback 👎 → dataset 追加 → re-eval → promote
