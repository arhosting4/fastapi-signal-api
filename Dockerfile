# filename: Dockerfile

# --- اسٹیج 1: بلڈر (Builder) ---
# اس اسٹیج کا مقصد انحصار کو محفوظ طریقے سے نصب کرنا ہے۔
FROM python:3.11-slim as builder

# کام کرنے کی ڈائرکٹری سیٹ کریں
WORKDIR /opt/venv

# ایک ورچوئل ماحول بنائیں
RUN python -m venv .

# ورچوئل ماحول کو PATH میں شامل کریں
ENV PATH="/opt/venv/bin:$PATH"

# انحصار کو کاپی کریں اور نصب کریں
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# --- اسٹیج 2: فائنل امیج (Final Image) ---
# یہ حتمی، ہلکا پھلکا امیج ہے جو پروڈکشن میں چلے گا۔
FROM python:3.11-slim

# کام کرنے کی ڈائرکٹری سیٹ کریں
WORKDIR /app

# غیر روٹ صارف بنائیں اور استعمال کریں (سیکیورٹی کے لیے بہترین عمل)
RUN addgroup --system nonroot && adduser --system --ingroup nonroot nonroot
USER nonroot

# بلڈر اسٹیج سے ورچوئل ماحول کاپی کریں
COPY --from=builder /opt/venv /opt/venv

# ایپلیکیشن کوڈ کاپی کریں
COPY . .

# ورچوئل ماحول کو PATH میں شامل کریں
ENV PATH="/opt/venv/bin:$PATH"

# ماحول کے متغیرات
# یہ متغیرات Render جیسے پلیٹ فارم پر اوور رائڈ کیے جائیں گے
ENV PORT=8000
ENV HOST="0.0.0.0"

# پورٹ کو ظاہر کریں
EXPOSE 8000

# ایپلیکیشن چلانے کا حکم
# Gunicorn ایک پروڈکشن-گریڈ سرور ہے
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app", "--bind", "0.0.0.0:8000"]
