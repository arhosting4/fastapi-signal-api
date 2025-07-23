from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routes.signal_routes import router as signal_router
from src.routes.news_routes import router as news_router
from src.routes.feedback_routes import router as feedback_router
from src.routes.trades_routes import router as trades_router

from src.database.models import create_db_and_tables

app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB tables
@app.on_event("startup")
def startup_event():
    create_db_and_tables()

# Include all API routers
app.include_router(signal_router, prefix="/api/signals")
app.include_router(news_router, prefix="/api/news")
app.include_router(feedback_router, prefix="/api/feedback")
app.include_router(trades_router, prefix="/api/trades")

# Root path test
@app.get("/")
def read_root():
    return {"message": "FastAPI Signal API is running!"}
