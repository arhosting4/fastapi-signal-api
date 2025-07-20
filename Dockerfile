# Python کا ایک مستحکم اور مکمل بنیادی امیج استعمال کریں
FROM python:3.9-bullseye

# ورکنگ ڈائرکٹری سیٹ کریں
WORKDIR /app

# سسٹم کو اپ ڈیٹ کریں اور TA-Lib کے لیے ضروری پیکیجز انسٹال کریں
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# TA-Lib کو ڈاؤن لوڈ، کمپائل اور انسٹال کریں
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# لنکر کیش کو اپ ڈیٹ کریں تاکہ سسٹم کو نئی لائبریری مل سکے
RUN ldconfig

# requirements.txt فائل کو کاپی کریں
COPY requirements.txt .

# پائیتھن کے انحصار کو انسٹال کریں
# اب ورژن لاک ہونے کی وجہ سے کوئی مطابقت کا مسئلہ نہیں آئے گا
RUN pip install --no-cache-dir -r requirements.txt

# باقی پروجیکٹ فائلوں کو کاپی کریں
COPY . .

# ایپلیکیشن کو چلانے کے لیے کمانڈ (Render اسے خود سنبھالے گا)
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app"]
