# filename: Dockerfile

# ★★★ مرحلہ 1: بنیادی امیج ★★★
# Python 3.11 کے سلم ورژن سے شروع کریں
FROM python:3.11-slim

# ★★★ مرحلہ 2: سسٹم-لیول ڈیپینڈنسیز ★★★
# apt کو اپ ڈیٹ کریں اور build-essential انسٹال کریں
# یہ pandas-ta جیسی لائبریریز کے لیے ضروری ہے
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ★★★ مرحلہ 3: ورکنگ ڈائرکٹری ★★★
# کنٹینر کے اندر ایک ورکنگ ڈائرکٹری بنائیں
WORKDIR /app

# ★★★ مرحلہ 4: پائیتھون ڈیپینڈنسیز ★★★
# پہلے requirements.txt کو کاپی کریں تاکہ Docker کیشنگ سے فائدہ اٹھایا جا سکے
COPY requirements.txt .

# requirements.txt میں دی گئی تمام لائبریریز انسٹال کریں
RUN pip install --no-cache-dir -r requirements.txt

# ★★★ مرحلہ 5: ایپلیکیشن کوڈ ★★★
# باقی تمام ایپلیکیشن کوڈ کو کاپی کریں
COPY . .

# ★★★ مرحلہ 6: کمانڈ ★★★
# Gunicorn سرور کو چلانے کے لیے کمانڈ
# Render خود بخود PORT ماحول متغیر فراہم کرتا ہے
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app", "--bind", "0.0.0.0:${PORT}"]
