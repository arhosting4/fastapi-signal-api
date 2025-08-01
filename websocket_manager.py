# filename: websocket_manager.py

import asyncio
import json
import logging
from typing import List, Dict, Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    WebSocket کنکشنز کو منظم کرنے کے لیے مرکزی کلاس۔
    یہ نئے کنکشنز کو قبول کرتی ہے، منقطع کرتی ہے، اور تمام فعال کنکشنز کو پیغامات نشر کرتی ہے۔
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """ایک نئے WebSocket کنکشن کو قبول کرتا ہے اور اسے فعال فہرست میں شامل کرتا ہے۔"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔌 نیا WebSocket کنکشن قائم ہوا۔ کل فعال کنکشنز: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """ایک WebSocket کنکشن کو فعال فہرست سے ہٹاتا ہے۔"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"🔌 WebSocket کنکشن منقطع ہوا۔ کل فعال کنکشنز: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """تمام فعال کنکشنز کو ایک JSON پیغام بھیجتا ہے۔"""
        if not self.active_connections:
            logger.debug("کوئی فعال WebSocket کنکشن نہیں، پیغام نشر نہیں کیا گیا۔")
            return

        # پیغام کو JSON سٹرنگ میں تبدیل کریں
        # یہ فرض کیا جاتا ہے کہ پیغام میں موجود ڈیٹا پہلے ہی سیریلائز ہو چکا ہے (جیسے datetime -> str)
        message_str = json.dumps(message)
        
        logger.info(f"📡 {len(self.active_connections)} فعال کنکشنز کو پیغام نشر کیا جا رہا ہے...")
        
        # تمام کنکشنز کو ایک ساتھ پیغام بھیجنے کے لیے ٹاسک بنائیں
        tasks = [connection.send_text(message_str) for connection in self.active_connections]
        
        # asyncio.gather کا استعمال کرتے ہوئے تمام ٹاسک چلائیں اور نتائج حاصل کریں
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # ناکام کنکشنز کو تلاش کریں اور انہیں ہٹائیں
        failed_connections = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                connection = self.active_connections[i]
                failed_connections.append(connection)
                logger.warning(f"ایک کنکشن کو پیغام بھیجنے میں ناکامی: {result}۔ کنکشن کو ہٹایا جا رہا ہے۔")

        for connection in failed_connections:
            self.disconnect(connection)

# مینیجر کا ایک عالمی نمونہ (Global Instance) بناتے ہیں تاکہ پوری ایپلیکیشن میں استعمال ہو سکے
manager = ConnectionManager()
            
