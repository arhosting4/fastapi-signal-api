# filename: Dockerfile

# مرحلہ 1: بنیادی امیج
FROM python:3.11-slim

# مرحلہ 2: سسٹم-لیول ڈیپینڈنسیز
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# مرحلہ 3: ورکنگ ڈائرکٹری
WORKDIR /app

# مرحلہ 4: پائیتھون ڈیپینڈنسیز
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# مرحلہ 5: ایپلیکیشن کوڈ
COPY . .

# مرحلہ 6: کمانڈ
# ★★★ اہم تبدیلی: CMD کو شیل فارم میں لکھا گیا ہے تاکہ ${PORT} کام کرے ★★★
CMD ["sh", "-c", "gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:${PORT}"]
