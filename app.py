from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database.models import create_db_and_tables
from src.routes import signal_routes, news_routes, feedback_routes, trades_routes
from sentinel import start_background_tasks

app = FastAPI(
    title="Crypto Signal API",
    description="Live crypto signals, financial news, user feedback, and trade records.",
    version="1.0.0"
)

# ✅ Allow frontend requests (CORS policy)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domain later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Mount all API routes
app.include_router(signal_routes.router, prefix="/signals", tags=["Signals"])
app.include_router(news_routes.router, prefix="/news", tags=["News"])
app.include_router(feedback_routes.router, prefix="/feedback", tags=["Feedback"])
app.include_router(trades_routes.router, prefix="/trades", tags=["Trades"])

# ✅ Setup database and scheduler on startup
@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
    start_background_tasks()
