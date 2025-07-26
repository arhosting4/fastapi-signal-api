# --- اسٹیج 1: بلڈ انوائرمنٹ ---
# پائتھن کا بیس امیج استعمال کریں
FROM python:3.11-slim as builder

# ورکنگ ڈائرکٹری سیٹ کریں
WORKDIR /app

# انحصار (dependencies) کے لیے ضروری پیکیجز انسٹال کریں
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt کو کاپی کریں اور انحصار انسٹال کریں
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# --- اسٹیج 2: فائنل امیج ---
# ایک چھوٹا اور محفوظ بیس امیج استعمال کریں
FROM python:3.11-slim

# ورکنگ ڈائرکٹری سیٹ کریں
WORKDIR /app

# PostgreSQL کلائنٹ انسٹال کریں (اگر ضرورت ہو)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# بلڈر اسٹیج سے وہیلز (wheels) کاپی کریں
COPY --from=builder /app/wheels /wheels

# وہیلز سے انحصار انسٹال کریں
RUN pip install --no-index --find-links=/wheels /wheels/*

# باقی تمام ایپلیکیشن کوڈ کاپی کریں
COPY . .

# Gunicorn کے لیے ماحول کے متغیرات سیٹ کریں
ENV MODULE_NAME="app:app"
ENV VARIABLE_NAME="app"
ENV LOG_LEVEL="info"

# پورٹ 8000 کو ایکسپوز کریں
EXPOSE 8000

# ایپلیکیشن چلانے کے لیے کمانڈ
# Render.com $PORT متغیر خود سیٹ کرتا ہے
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "app:app"]
