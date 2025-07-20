# Python کا بنیادی امیج منتخب کریں
FROM python:3.9-slim

# ورکنگ ڈائرکٹری سیٹ کریں
WORKDIR /app

# --- اہم اور حتمی اصلاح: TA-Lib کو انسٹال کریں ---
# 1. TA-Lib کو کمپائل کرنے کے لیے ضروری پیکیجز انسٹال کریں
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 2. TA-Lib کو ڈاؤن لوڈ، کمپائل اور انسٹال کریں
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# requirements.txt کو کاپی کریں
COPY requirements.txt .

# --- پائیتھن کے انحصار کو انسٹال کریں (بشمول TA-Lib ریپر) ---
RUN pip install --no-cache-dir -r requirements.txt

# باقی پروجیکٹ فائلوں کو کاپی کریں
COPY . .

# ایپلیکیشن کو چلانے کے لیے کمانڈ
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app"]
