# filename: fusion_engine.py

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from schemas import Candle
from utils import convert_candles_to_dataframe
from scoring_engine import get_scored_signal # نیا، واحد انجن

logger = logging.getLogger(__name__)

async def generate_final_signal(
    db: Session, 
    symbol: str, 
    candles: List[Candle], 
    symbol_personality: Dict
) -> Dict[str, Any]:
    """
    یہ فیوژن انجن اب صرف ایک گیٹ وے کے طور پر کام کرتا ہے جو اسکورنگ انجن کو کال کرتا ہے۔
    """
    try:
        df = convert_candles_to_dataframe(candles)
        if df.empty:
            return {"status": "no-signal", "reason": "ناکافی ڈیٹا"}

        # براہِ راست اسکورنگ انجن کو کال کریں
        signal_result = get_scored_signal(df, symbol, symbol_personality)
        
        return signal_result

    except Exception as e:
        logger.error(f"[{symbol}] کے لیے فیوژن انجن میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
        return {"status": "error", "reason": "AI فیوژن میں ایک غیر متوقع خرابی۔"}
        
