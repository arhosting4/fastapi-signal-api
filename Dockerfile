# filename: Dockerfile

# --- اسٹیج 1: بلڈر ---
# انحصار کو انسٹال کرنے کے لیے ایک مکمل Python امیج کا استعمال کریں
FROM python:3.10-slim as builder

# کام کرنے کی ڈائرکٹری سیٹ کریں
WORKDIR /app

# ماحولیاتی متغیرات
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# سسٹم کے انحصار کو اپ ڈیٹ کریں اور بلڈ کے لیے ضروری ٹولز انسٹال کریں
RUN apt-get update && apt-get install -y --no-install-recommends gcc

# انحصار کو ایک ورچوئل ماحول میں انسٹال کریں
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- اسٹیج 2: رنر ---
# ایک چھوٹی، ہلکی پھلکی امیج پر سوئچ کریں
FROM python:3.10-slim

# کام کرنے کی ڈائرکٹری سیٹ کریں
WORKDIR /app

# بلڈر اسٹیج سے ورچوئل ماحول کو کاپی کریں
COPY --from=builder /opt/venv /opt/venv

# غیر روٹ صارف بنائیں اور استعمال کریں
RUN useradd --create-home appuser
USER appuser

# ایپلیکیشن کوڈ کو کاپی کریں
COPY --chown=appuser:appuser . .

# ورچوئل ماحول کو PATH میں شامل کریں
ENV PATH="/opt/venv/bin:$PATH"

# ایپلیکیشن کو چلانے کے لیے پورٹ کو ظاہر کریں
EXPOSE 8000

# ایپلیکیشن کو gunicorn کے ساتھ چلائیں
# --workers 1: چونکہ شیڈولر صرف ایک ورکر کے لیے ڈیزائن کیا گیا ہے
# --worker-class uvicorn.workers.UvicornWorker: غیر مطابقت پذیر کوڈ کے لیے
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "app:app", "-b", "0.0.0.0:8000"]
