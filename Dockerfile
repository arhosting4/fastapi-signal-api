# ---- Stage 1: Build Stage ----
# Python کا ایک مستحکم ورژن استعمال کریں
FROM python:3.10-slim as builder

# کام کرنے کی ڈائرکٹری سیٹ کریں
WORKDIR /app

# ماحولیاتی متغیرات سیٹ کریں
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# سسٹم کی انحصار کو اپ ڈیٹ اور انسٹال کریں (اگر ضرورت ہو)
# RUN apt-get update && apt-get install -y build-essential

# پائپ کو اپ گریڈ کریں
RUN pip install --upgrade pip

# انحصار کی فائل کاپی کریں
COPY requirements.txt .

# انحصار کو انسٹال کریں
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# ---- Stage 2: Final Stage ----
# ایک چھوٹا اور محفوظ بیس امیج استعمال کریں
FROM python:3.10-slim

# کام کرنے کی ڈائرکٹری بنائیں
WORKDIR /app

# پہلے مرحلے سے انحصار کو کاپی کریں
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# وہیلز سے انحصار انسٹال کریں
RUN pip install --no-cache /wheels/*

# ایپلیکیشن کا کوڈ کاپی کریں
COPY . .

# فرنٹ اینڈ ڈائرکٹری کی موجودگی کو یقینی بنائیں
RUN mkdir -p frontend
COPY frontend/ /app/frontend/

# ایپلیکیشن کو چلانے کے لیے Gunicorn سرور کا استعمال کریں
# Render.com خود بخود PORT متغیر فراہم کرتا ہے
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:10000", "app:app"]
