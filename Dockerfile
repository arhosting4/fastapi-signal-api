# filename: Dockerfile

# Python 3.11 کے سلم ورژن سے شروع کریں
FROM python:3.11-slim

# کنٹینر کے اندر ایک ورکنگ ڈائرکٹری بنائیں
WORKDIR /app

# پہلے requirements.txt کو کاپی کریں
COPY requirements.txt .

# requirements.txt میں دی گئی تمام لائبریریز انسٹال کریں
RUN pip install --no-cache-dir -r requirements.txt

# باقی تمام ایپلیکیشن کوڈ کو کاپی کریں
COPY . .

# Gunicorn سرور کو چلانے کے لیے کمانڈ
CMD ["sh", "-c", "gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:${PORT}"]
