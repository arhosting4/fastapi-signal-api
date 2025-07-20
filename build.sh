#!/usr/bin/env bash
# exit on error
set -o errexit

# --- TA-Lib کو انسٹال کرنے کے لیے ضروری پیکیجز ---
apt-get update && apt-get install -y build-essential wget
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
make install
cd ..

# --- پائیتھن کے انحصار کو انسٹال کریں ---
pip install -r requirements.txt
