# filename: websocket_manager.py

from fastapi import WebSocket
from typing import List, Dict, Any
import logging
import json
import asyncio  # ★★★ لازمی، کیونکہ asyncio.gather استعمال ہو رہا ہے ★★★
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    WebSocket کنکشنز کو منظم کرنے کے لیے مرکزی کلاس (multi-client real-time broadcast, audit-ready).
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """ایک نئے WebSocket کلائنٹ کو قبول (register) کرتا ہے۔"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"نیا WebSocket کنکشن قائم ہوا۔ کل کنکشنز: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """کوئی کنکشن نکل جائے (disconnect) تو فوراً pool سے خارج۔"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket کنکشن منقطع ہوا۔ کل کنکشنز: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """
        تمام فعال کنکشنز کو پاک/سریر میں (JSON) پیغام بھیجتا ہے۔
        ناکام کنکشنز کو اوٹومیٹکلی remove کر دیتا ہے۔
        """
        # datetime objects کو serialize کرنے کے لیے خصوصی ہینڈلر
        def json_default(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
        
        try:
            # Default: ensure_ascii=False تاکہ اردو و حیرت انگیز JSON فیلڈز درست رہیں
            message_str = json.dumps(message, ensure_ascii=False, default=json_default)
        except Exception as e:
            logger.error(f"WebSocket پیغام سیریلائز کرنے میں ناکامی: {e}", exc_info=True)
            return

        if not self.active_connections:
            logger.info("کوئی فعال WebSocket کنکشن نہیں، پیغام نہیں بھیجا گیا۔")
            return

        logger.info(f"{len(self.active_connections)} فعال کنکشنز کو پیغام بھیجا جا رہا ہے...")
        tasks = [connection.send_text(message_str) for connection in self.active_connections]
        failed_connections = []
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                connection = self.active_connections[i]
                failed_connections.append(connection)
                logger.warning(f"کنکشن پر error: {result}")

        for connection in failed_connections:
            self.disconnect(connection)  # disconnect via central method

# گلوبل instance باقی ایپ میں centralized (import کر کے) استعمال کریں
manager = ConnectionManager()
                   
