# filename: roster_manager.py

import logging
from datetime import datetime
from typing import List, Tuple

from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from config import trading_settings

logger = logging.getLogger(__name__)

def _get_current_pair_lists() -> Tuple[List[str], List[str]]:
    """
    موجودہ دن (ہفتے کا دن یا اختتام ہفتہ) کی بنیاد پر بنیادی اور بیک اپ جوڑوں کی فہرستیں واپس کرتا ہے۔
    """
    # 0 = پیر, 6 = اتوار
    is_weekend = datetime.utcnow().weekday() >= 5
    
    if is_weekend:
        primary = trading_settings.WEEKEND_PRIMARY
        backup = trading_settings.WEEKEND_BACKUP
        logger.debug("اختتام ہفتہ کے جوڑوں کا انتخاب کیا گیا۔")
    else:
        primary = trading_settings.WEEKDAY_PRIMARY
        backup = trading_settings.WEEKDAY_BACKUP
        logger.debug("ہفتے کے دن کے جوڑوں کا انتخاب کیا گیا۔")
        
    return primary, backup

def get_hunting_roster(db: Session) -> List[str]:
    """
    شکاری انجن کے لیے تجزیہ کرنے والے جوڑوں کی متحرک فہرست تیار کرتا ہے۔
    یہ صرف ان بنیادی جوڑوں کو واپس کرتا ہے جن کا کوئی فعال سگنل نہیں ہے۔
    """
    primary_pairs, _ = _get_current_pair_lists()
    
    # ڈیٹا بیس سے تمام فعال سگنلز کی علامتیں حاصل کریں
    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    # بنیادی جوڑوں میں سے صرف وہ جوڑے منتخب کریں جو فعال نہیں ہیں
    hunting_roster = [p for p in primary_pairs if p not in active_symbols]
    
    if hunting_roster:
        logger.info(f"🏹 شکاری روسٹر تیار: {len(hunting_roster)} جوڑے تجزیے کے لیے - {hunting_roster}")
    else:
        logger.info("🏹 شکاری روسٹر: تمام بنیادی جوڑوں کے سگنل فعال ہیں۔ نئے تجزیے کی ضرورت نہیں۔")
        
    return hunting_roster

# نوٹ: get_split_monitoring_roster فنکشن کی اب ضرورت نہیں رہی کیونکہ ہمارا نیا ڈیزائن
# تمام فعال سگنلز کو ایک ساتھ چیک کرتا ہے۔ اس لیے اسے ہٹا دیا گیا ہے تاکہ کوڈ صاف رہے۔
