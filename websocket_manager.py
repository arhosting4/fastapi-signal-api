# filename: websocket_manager.py

from fastapi import WebSocket
from typing import List, Dict, Any
import logging
import json
import asyncio

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    WebSocket کنکشنز کو منظم کرنے کے لیے مرکزی کلاس۔
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """ایک نئے WebSocket کنکشن کو قبول کرتا ہے اور اسے فہرست میں شامل کرتا ہے۔"""
        # --- ★★★ خودکار اصلاح: گمشدہ لائنیں شامل کی گئیں ★★★ ---
        await websocket.accept()
        self.active_connections.append(websocket)
        # ---------------------------------------------------------
        logger.info(f"نیا WebSocket کنکشن قائم ہوا۔ کل فعال کنکشنز: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """ایک WebSocket کنکشن کو منقطع کرتا ہے۔"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket کنکشن منقطع ہوا۔ کل فعال کنکشنز: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """تمام فعال کنکشنز کو ایک پیغام بھیجتا ہے۔"""
        # پیغام کو JSON سٹرنگ میں تبدیل کریں
        message_str = json.dumps(message, ensure_ascii=False)
        
        if not self.active_connections:
            logger.info("کوئی فعال WebSocket کنکشن نہیں، براڈکاسٹ نہیں بھیجا گیا۔")
            return

        logger.info(f"{len(self.active_connections)} فعال کنکشنز کو پیغام بھیجا جا رہا ہے...")
        
        # تمام کنکشنز کو ایک ساتھ پیغام بھیجنے کے لیے ٹاسک بنائیں
        tasks = [connection.send_text(message_str) for connection in self.active_connections]
        
        # ناکام یا منقطع کنکشنز کو ٹریک کرنے کے لیے ایک فہرست
        failed_connections = []
        
        # asyncio.gather کا استعمال کرتے ہوئے تمام ٹاسک چلائیں
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                connection = self.active_connections[i]
                failed_connections.append(connection)
                logger.warning(f"ایک کنکشن کو پیغام بھیجنے میں ناکامی: {result}")

        # ناکام کنکشنز کو فعال فہرست سے ہٹا دیں
        for connection in failed_connections:
            # یہ چیک کرنا ضروری ہے کہ آیا کنکشن اب بھی فہرست میں ہے
            if connection in self.active_connections:
                self.active_connections.remove(connection)
                logger.info("ایک ناکام/منقطع کنکشن کو فہرست سے ہٹا دیا گیا۔")

# مینیجر کا ایک عالمی نمونہ (Global Instance) بناتے ہیں تاکہ اسے پورے پروجیکٹ میں استعمال کیا جا سکے
manager = ConnectionManager()
                
