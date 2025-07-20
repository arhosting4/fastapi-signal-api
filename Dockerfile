# Python کا بنیادی امیج منتخب کریں
FROM python:3.9-slim

# ورکنگ ڈائرکٹری سیٹ کریں
WORKDIR /app

# --- TA-Lib کو انسٹال کرنے کے لیے ضروری پیکیجز ---
# --no-install-recommends کا استعمال امیج کا سائز کم رکھتا ہے
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# --- TA-Lib کو ڈاؤن لوڈ، کمپائل اور انسٹال کریں ---
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# --- اہم اور حتمی اصلاح: لنکر کیش کو اپ ڈیٹ کریں ---
# یہ کمانڈ سسٹم کو بتاتی ہے کہ نئی انسٹال شدہ ta-lib لائبریری کہاں ہے
RUN ldconfig

# requirements.txt کو کاپی کریں
COPY requirements.txt .

# --- پائیتھن کے انحصار کو انسٹال کریں ---
# اب pip کو ta-lib لائبریری مل جائے گی
RUN pip install --no-cache-dir -r requirements.txt

# باقی پروجیکٹ فائلوں کو کاپی کریں
COPY . .

# ایپلیکیشن کو چلانے کے لیے کمانڈ
# Render.com کے لیے gunicorn کی ڈیفالٹ کمانڈ کو استعمال کریں گے
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app"]
# Render کی ڈیفالٹ کمانڈ کو اووررائڈ کرنے کی ضرورت نہیں اگر وہ پہلے سے سیٹ ہے
