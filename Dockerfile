# Python کا ایک موثر اور مستحکم بنیادی امیج استعمال کریں
FROM python:3.9-slim-bullseye

# ورکنگ ڈائرکٹری سیٹ کریں
WORKDIR /app

# requirements.txt فائل کو کاپی کریں
COPY requirements.txt .

# پائیتھن کے انحصار کو انسٹال کریں
RUN pip install --no-cache-dir -r requirements.txt

# باقی پروجیکٹ فائلوں کو کاپی کریں
COPY . .

# ایپلیکیشن کو چلانے کے لیے کمانڈ
# Render.com اس کمانڈ کو خود سنبھالے گا اگر اس کی سیٹنگز میں وضاحت کی گئی ہے
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app"]
