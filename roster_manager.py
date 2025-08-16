import logging
from datetime import datetime
from typing import List, Tuple, Set

from sqlalchemy.orm import Session

import database_crud as crud
from config import trading_settings

logger = logging.getLogger(__name__)

# ★★★ نیا فنکشن جو app.py کو چاہیے ★★★
def get_forex_pairs() -> List[str]:
    """
    کنفیگریشن سے فاریکس جوڑوں کی فہرست واپس کرتا ہے۔
    """
    return trading_settings.WEEKDAY_PRIMARY

def get_crypto_pairs() -> List[str]:
    """
    کنفیگریشن سے کرپٹو جوڑوں کی فہرست واپس کرتا ہے۔
    """
    return trading_settings.WEEKEND_PRIMARY

def get_hunting_roster(db: Session) -> List[str]:
    """
    شکاری انجن کے لیے تجزیہ کرنے والے جوڑوں کی متحرک فہرست تیار کرتا ہے۔
    """
    is_weekend = datetime.utcnow().weekday() >= 5  # 5 = Saturday, 6 = Sunday
    
    if is_weekend:
        primary_pairs = get_crypto_pairs()
        log_prefix = "کرپٹو"
    else:
        primary_pairs = get_forex_pairs()
        log_prefix = "فاریکس"

    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    available_to_hunt = [p for p in primary_pairs if p not in active_symbols]
    
    if not available_to_hunt:
        logger.info(f"🏹 شکاری روسٹر ({log_prefix}): تمام فعال جوڑوں کے سگنل لائیو ہیں۔")
        return []

    logger.info(f"🏹 شکاری روسٹر ({log_prefix}): {len(available_to_hunt)} جوڑے تجزیے کے لیے۔")
    return available_to_hunt

# یہ فنکشن اب استعمال میں نہیں ہے، لیکن ہم اسے مستقبل کے لیے رکھ سکتے ہیں۔
def get_split_monitoring_roster(db: Session, active_symbols_to_check: Set[str]) -> Tuple[List[str], List[str]]:
    """
    نگرانی کے لیے جوڑوں کو دو فہرستوں میں تقسیم کرتا ہے۔
    """
    primary_pairs, _ = _get_current_pair_lists()
    inactive_primary_pairs = [p for p in primary_pairs if p not in active_symbols_to_check]
    return list(active_symbols_to_check), inactive_primary_pairs

# یہ اندرونی فنکشن بھی اب براہ راست استعمال نہیں ہو رہا
def _get_current_pair_lists() -> Tuple[List[str], List[str]]:
    """
    موجودہ دن کی بنیاد پر بنیادی اور بیک اپ جوڑوں کی فہرستیں واپس کرتا ہے۔
    """
    is_weekend = datetime.utcnow().weekday() >= 5
    
    if is_weekend:
        primary = trading_settings.WEEKEND_PRIMARY
        backup = trading_settings.WEEKEND_BACKUP
    else:
        primary = trading_settings.WEEKDAY_PRIMARY
        backup = trading_settings.WEEKDAY_BACKUP
        
    return primary, backup
    
