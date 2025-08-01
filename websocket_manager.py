class ConnectionManager:
    """
    WebSocket کنکشنز کو منظم کرنے کے لیے مرکزی کلاس۔
    یہ تمام کنکشنز کو جوڑتی، منقطع کرتی اور پیغامات بھیجتی ہے۔
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔗 نیا WebSocket کنکشن قائم ہوا۔ کل: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"❌ WebSocket کنکشن منقطع۔ باقی کنکشنز: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        def json_default(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        message_str = json.dumps(message, ensure_ascii=False, default=json_default)

        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning(f"⚠️ WebSocket پیغام بھیجنے میں خرابی: {e}")
