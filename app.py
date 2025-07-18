from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# 1. Render کے ہیلتھ چیک کے لیے اینڈ پوائنٹ
@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

# 2. اسٹیٹک فائلوں کو پیش کرنے کے لیے ماؤنٹنگ
# یہ یقینی بنائے گا کہ index.html اور دیگر فائلیں مل سکیں
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# 3. روٹ پیج (index.html) کو پیش کرنے کے لیے اینڈ پوائنٹ
@app.get("/", response_class=FileResponse)
async def read_root():
    # یہ یقینی بنائیں کہ آپ کی index.html فائل 'frontend' فولڈر کے اندر ہے
    return "frontend/index.html"

# باقی تمام کوڈ (yfinance, scheduler, api/signal) کو عارضی طور پر ہٹا دیا گیا ہے
# تاکہ ہم صرف ڈیپلائمنٹ کے مسئلے پر توجہ مرکوز کر سکیں۔
