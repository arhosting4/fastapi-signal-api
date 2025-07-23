from fastapi import FastAPI from fastapi.middleware.cors import CORSMiddleware from src.routes.signal_routes import router as signal_router from src.routes.news_routes import router as news_router from src.routes.feedback_routes import router as feedback_router from src.routes.trades_routes import router as trades_router from src.database.models import create_db_and_tables

app = FastAPI()

Allow CORS for frontend

app.add_middleware( CORSMiddleware, allow_origins=[""], allow_credentials=True, allow_methods=[""], allow_headers=["*"], )

@app.on_event("startup") def on_startup(): create_db_and_tables()

Include routers

app.include_router(signal_router, prefix="/api/signal", tags=["Signal"]) app.include_router(news_router, prefix="/api/news", tags=["News"]) app.include_router(feedback_router, prefix="/api/feedback", tags=["Feedback"]) app.include_router(trades_router, prefix="/api/trades", tags=["Trades"])

@app.get("/") def root(): return {"message": "Signal API Live - Render Deployment Working"}
