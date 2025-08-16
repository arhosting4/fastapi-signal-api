import logging
from datetime import datetime
from typing import List, Tuple, Set

from sqlalchemy.orm import Session

import database_crud as crud
from config import trading_settings

logger = logging.getLogger(__name__)

def get_forex_pairs() -> List[str]:
    """کنفیگریشن سے فاریکس جوڑوں کی فہرست واپس کرتا ہے۔"""
    return trading_settings.WEEKDAY_PRIMARY

def get_crypto_pairs() -> List[str]:
    """کنفیگریشن سے کرپٹو جوڑوں کی فہرست واپس کرتا ہے۔"""
    return trading_settings.WEEKEND_PRIMARY

# ★★★ یہ ہے وہ فنکشن جو غائب تھا ★★★
def get_active_trading_pairs() -> List[str]:
    """
    موجودہ دن کی بنیاد پر ٹریڈنگ کے لیے تمام ممکنہ جوڑوں کی فہرست واپس کرتا ہے۔
    یہ key_manager کو بتاتا ہے کہ کن جوڑوں کے لیے کلیدیں تیار کرنی ہیں۔
    """
    is_weekend = datetime.utcnow().weekday() >= 5
    if is_weekend:
        return get_crypto_pairs()
    else:
        return get_forex_pairs()

def get_hunting_roster(db: Session) -> List[str]:
    """شکاری انجن کے لیے تجزیہ کرنے والے جوڑوں کی متحرک فہرست تیار کرتا ہے۔"""
    active_pairs_for_today = get_active_trading_pairs()
    log_prefix = "کرپٹو" if datetime.utcnow().weekday() >= 5 else "فاریکس"

    active_signals_in_db = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    available_to_hunt = [p for p in active_pairs_for_today if p not in active_signals_in_db]
    
    if not available_to_hunt:
        logger.info(f"🏹 شکاری روسٹر ({log_prefix}): تمام فعال جوڑوں کے سگنل لائیو ہیں۔")
        return []

    logger.info(f"🏹 شکاری روسٹر ({log_prefix}): {len(available_to_hunt)} جوڑے تجزیے کے لیے۔")
    return available_to_hunt
    
