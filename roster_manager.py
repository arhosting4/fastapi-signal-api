# filename: roster_manager.py

import logging
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from config import trading_settings

logger = logging.getLogger(__name__)

def get_active_trading_pairs() -> List[str]:
    """
    موجودہ دن کی بنیاد پر فعال ٹریڈنگ جوڑوں (فاریکس یا کرپٹو) کی فہرست واپس کرتا ہے۔
    """
    # 0 = پیر, 4 = جمعہ, 5 = ہفتہ, 6 = اتوار
    current_weekday = datetime.utcnow().weekday()
    
    # ہفتے کے دن (پیر سے جمعہ)
    if 0 <= current_weekday <= 4:
        # logger.debug("ہفتے کے دن کا روسٹر فعال: فاریکس جوڑے۔")
        return trading_settings.WEEKDAY_PRIMARY + trading_settings.WEEKDAY_BACKUP
    # اختتامِ ہفتہ (ہفتہ اور اتوار)
    else:
        # logger.debug("اختتامِ ہفتہ کا روسٹر فعال: کرپٹو جوڑے۔")
        return trading_settings.WEEKEND_PRIMARY + trading_settings.WEEKEND_BACKUP

def get_hunting_roster(db: Session) -> List[str]:
    """
    شکاری انجن کے لیے صرف ان فعال جوڑوں کی فہرست تیار کرتا ہے جن کا کوئی سگنل لائیو نہیں ہے۔
    """
    todays_pairs = get_active_trading_pairs()
    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    # صرف ان جوڑوں کو منتخب کریں جو آج کے فعال جوڑوں میں سے ہیں اور جن کا سگنل لائیو نہیں ہے
    hunting_roster = [p for p in todays_pairs if p not in active_symbols]
    
    market_type = 'فاریکس' if datetime.utcnow().weekday() <= 4 else 'کرپٹو'
    
    if hunting_roster:
        logger.info(f"🏹 شکاری روسٹر ({market_type}): {len(hunting_roster)} جوڑے تجزیے کے لیے۔")
    else:
        logger.info(f"🏹 شکاری روسٹر ({market_type}): تمام فعال جوڑوں کے سگنل لائیو ہیں۔")
        
    return hunting_roster
    
