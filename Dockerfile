# Python کا ایک زیادہ مکمل، لیکن پھر بھی موثر، بنیادی امیج استعمال کریں
FROM python:3.9-bullseye

# ورکنگ ڈائرکٹری سیٹ کریں
WORKDIR /app

# --- TA-Lib کو انسٹال کرنے کے لیے ضروری پیکیجز ---
# apt-get کو ایک ہی RUN کمانڈ میں استعمال کرنا کیشنگ کو بہتر بناتا ہے
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

# --- اہم اور حتمی اصلاح: TA-Lib کے راستے کے لیے ماحولیاتی متغیرات سیٹ کریں ---
# یہ pip کو بتاتا ہے کہ C ہیڈر فائلیں اور لائبریریاں کہاں تلاش کرنی ہیں
ENV TA_LIBRARY_PATH=/usr/lib
ENV TA_INCLUDE_PATH=/usr/include

# requirements.txt کو کاپی کریں
COPY requirements.txt .

# --- پائیتھن کے انحصار کو انسٹال کریں ---
# اب pip کو TA-Lib کو تلاش کرنے میں کوئی مسئلہ نہیں ہوگا
RUN pip install --no-cache-dir -r requirements.txt

# باقی پروجیکٹ فائلوں کو کاپی کریں
COPY . .

# ایپلیکیشن کو چلانے کے لیے کمانڈ
# Render.com اس کمانڈ کو خود سنبھال لے گا اگر اس کی سیٹنگز میں وضاحت کی گئی ہے
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app"]
