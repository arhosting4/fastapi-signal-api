# Python کا ایک مستحکم اور مکمل بنیادی امیج استعمال کریں
FROM python:3.9-bullseye

# ماحولیاتی متغیرات تاکہ apt-get غیر ضروری سوالات نہ پوچھے
ENV DEBIAN_FRONTEND=noninteractive

# ورکنگ ڈائرکٹری سیٹ کریں
WORKDIR /app

# سسٹم کو اپ ڈیٹ کریں اور TA-Lib کے لیے تمام ضروری پیکیجز انسٹال کریں
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# TA-Lib کو ڈاؤن لوڈ اور انسٹال کرنے کا سب سے قابل اعتماد طریقہ
# ہم سورس کوڈ کو /tmp میں ڈاؤن لوڈ کریں گے اور پھر اسے صاف کر دیں گے
WORKDIR /tmp
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/usr && \
    make && \
    make install

# واپس اپنی ایپلیکیشن ڈائرکٹری میں جائیں
WORKDIR /app

# لنکر کیش کو اپ ڈیٹ کریں تاکہ سسٹم کو نئی لائبریری مل سکے
RUN ldconfig

# requirements.txt فائل کو کاپی کریں
COPY requirements.txt .

# پائیتھن کے انحصار کو انسٹال کریں
# اب pandas-ta کا تازہ ترین ورژن بھی TA-Lib کو تلاش کر لے گا
RUN pip install --no-cache-dir -r requirements.txt

# باقی پروجیکٹ فائلوں کو کاپی کریں
COPY . .

# ایپلیکیشن کو چلانے کے لیے کمانڈ
# Render اس کمانڈ کو خود سنبھالے گا اگر اس کی سیٹنگز میں وضاحت کی گئی ہے
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app"]
