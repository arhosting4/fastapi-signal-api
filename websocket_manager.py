# filename: websocket_manager.py

from fastapi import WebSocket
from typing import List, Dict, Any
import logging
import json
import asyncio  # ★★★ یہ لائن سب سے اہم ہے اور اسے شامل کیا گیا ہے ★★★

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    WebSocket کنکشنز کو منظم کرنے کے لیے مرکزی کلاس۔
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """ایک نئے WebSocket کنکشن کو قبول کرتا ہے۔"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"نیا WebSocket کنکشن قائم ہوا۔ کل کنکشنز: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """ایک WebSocket کنکشن کو منقطع کرتا ہے۔"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket کنکشن منقطع ہوا۔ کل کنکشنز: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """تمام فعال کنکشنز کو ایک پیغام بھیجتا ہے۔"""
        # datetime آبجیکٹس کو ہینڈل کرنے کے لیے ایک کسٹم JSON انکوڈر
        def json_default(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        # ہم نے models.py میں تبدیلی کر دی ہے، لیکن یہ ایک اضافی حفاظتی تہہ ہے
        message_str = json.dumps(message, ensure_ascii=False)
        
        if not self.active_connections:
            logger.info("کوئی فعال WebSocket کنکشن نہیں، پیغام نہیں بھیجا گیا۔")
            return

        logger.info(f"{len(self.active_connections)} فعال کنکشنز کو پیغام بھیجا جا رہا ہے...")
        tasks = [connection.send_text(message_str) for connection in self.active_connections]
        
        failed_connections = []
        
        # ★★★ اب asyncio.gather کام کرے گا کیونکہ asyncio امپورٹ ہو چکا ہے ★★★
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                connection = self.active_connections[i]
                failed_connections.append(connection)
                logger.warning(f"ایک کنکشن کو پیغام بھیجنے میں ناکامی: {result}")

        for connection in failed_connections:
            self.disconnect(connection) # منقطع کرنے کے لیے مرکزی فنکشن کا استعمال کریں

# مینیجر کا ایک عالمی نمونه (Global Instance) بناتے ہیں
manager = ConnectionManager()
