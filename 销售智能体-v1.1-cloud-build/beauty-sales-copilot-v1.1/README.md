# 美容医美 AI 销售副驾 V1.1 — 开发起步工程

包含 Android Kotlin / Jetpack Compose 导航页面、FastAPI **沙盒**交易接口、PostgreSQL 初始化 SQL、Docker Compose、本地自动化测试。

## 快速测试（Python）
```bash
cd backend
pip install -r requirements.txt
pytest -q
DEMO_API_KEY=local-dev-only uvicorn app.main:app --reload
```
浏览 http://127.0.0.1:8000/docs；除 `/health` 外，接口需请求头 `X-Demo-Key: local-dev-only`。
`topup-demo` 和 `checkout-demo` 仅模拟资金，不连接实际支付。下单或模拟充值必须带 `Idempotency-Key` 请求头。

## Docker + PostgreSQL
将 `.env.example` 复制为 `.env` 并更换为安全随机密钥，再执行 `docker compose up --build`。初次启动 API 会按 ORM 创建表。`backend/migrations/001_initial_postgres.sql` 是供人工检视及空库手动初始化使用的 DDL，**不要与自动建表重复执行**。正式版本应改用有序 Alembic 迁移。

## Android
使用 Android Studio 打开 `android-app/` 目录，等待 Gradle 同步；需要 Android SDK 35 和 JDK 17。执行 `./gradlew assembleDebug` 前需要本机 Gradle Wrapper（当前环境无 Android SDK/Gradle，未附 wrapper jar）。可在 Android Studio 使用本机 Gradle 或生成 wrapper。该 APP 当前是可编译目标的 UI 骨架，API 尚未连接，不是完整可运行的销售产品。

## 开发下一阶段
完成正式认证和租户/角色权限、Android API 集成、WebSocket ASR 实时助手、知识库、钱包双分录/行锁、真实支付回调及对账、部分退款与项目履约、合规审批。详见 `docs/规则冻结.md`。

## GitHub Actions 云端生成调试 APK
将此工程的所有文件（包括 `.github/workflows/android-debug-apk.yml`）上传至自己的 GitHub 仓库；在 **Actions → Build Android Debug APK → Run workflow** 运行。构建成功后，从该次运行的 **Artifacts** 下载 `beauty-sales-copilot-v1.1-debug-apk`，其中包含 `app-debug.apk`。这属于测试安装包，不是正式发布签名包。此工作流尚未在 GitHub Actions 执行验证。
