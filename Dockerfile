# filename: render.yaml
services:
  - type: web
    name: scalpmaster-ai-api
    env: docker  # <-- یہاں تبدیلی کریں
    region: oregon
    plan: free
    branch: main
    # buildCommand اور startCommand کو ہٹا دیں کیونکہ Dockerfile انہیں سنبھالتا ہے
    healthCheckPath: /health
    dockerfilePath: ./Dockerfile # <-- Dockerfile کا راستہ
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: scalpmaster-db
          property: connectionString
      - key: TWELVE_DATA_API_KEYS
        sync: false
      - key: MARKETAUX_API_KEY
        sync: false
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: TELEGRAM_CHAT_ID
        sync: false

databases:
  - name: scalpmaster-db
    databaseName: scalpmaster_db
    user: scalpmaster_user
    plan: free
