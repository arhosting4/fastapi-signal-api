# filename: roster_manager.py

import logging
from datetime import datetime
from typing import List, Tuple, Set

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
    یہ ان بنیادی جوڑوں کو ترجیح دیتا ہے جن کا کوئی فعال سگنل نہیں ہے،
    اور اگر ضرورت ہو تو بیک اپ جوڑوں سے خالی جگہیں پر کرتا ہے۔
    """
    primary_pairs, backup_pairs = _get_current_pair_lists()
    roster_size = len(primary_pairs)
    
    # ڈیٹا بیس سے تمام فعال سگنلز کی علامتیں حاصل کریں
    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    # بنیادی جوڑوں میں سے وہ جوڑے منتخب کریں جو فعال نہیں ہیں
    available_primary = [p for p in primary_pairs if p not in active_symbols]
    
    # بیک اپ جوڑوں میں سے وہ جوڑے منتخب کریں جو فعال نہیں ہیں
    available_backup = [p for p in backup_pairs if p not in active_symbols]
    
    # شکاری روسٹر کو دستیاب بنیادی جوڑوں سے شروع کریں
    hunting_roster = available_primary
    
    # اگر روسٹر کا سائز بنیادی جوڑوں کی تعداد سے کم ہے، تو بیک اپ جوڑوں سے شامل کریں
    needed = roster_size - len(hunting_roster)
    if needed > 0:
        hunting_roster.extend(available_backup[:needed])
        
    logger.info(f"🏹 شکاری روسٹر تیار: {len(hunting_roster)} جوڑے - {hunting_roster}")
    return hunting_roster

def get_split_monitoring_roster(db: Session, active_symbols_to_check: Set[str]) -> Tuple[List[str], List[str]]:
    """
    نگرانی کے لیے جوڑوں کو دو فہرستوں میں تقسیم کرتا ہے تاکہ API کالز کو بہتر بنایا جا سکے۔

    1.  **OHLC کے لیے فعال جوڑے:** وہ جوڑے جن کا فعال سگنل ہے (درست TP/SL جانچ کے لیے مکمل کینڈل ڈیٹا درکار ہے)۔
    2.  **کوٹ کے لیے غیر فعال جوڑے:** وہ جوڑے جو بنیادی فہرست میں ہیں لیکن فعال نہیں ہیں (ان کی صرف فوری قیمت کی اپ ڈیٹ کافی ہے)۔
    
    Returns:
        Tuple[List[str], List[str]]: (OHLC کے لیے جوڑے, فوری کوٹ کے لیے جوڑے)
    """
    primary_pairs, _ = _get_current_pair_lists()
    
    # غیر فعال بنیادی جوڑے = بنیادی جوڑوں کی فہرست میں سے وہ جوڑے جو نگرانی کی فہرست میں نہیں ہیں
    inactive_primary_pairs = [p for p in primary_pairs if p not in active_symbols_to_check]
    
    logger.debug("🛡️ تقسیم شدہ نگرانی روسٹر تیار:")
    logger.debug(f"   - درست جانچ کے لیے (فعال سگنلز): {list(active_symbols_to_check)}")
    logger.debug(f"   - قیمت اپ ڈیٹ کے لیے (غیر فعال بنیادی): {inactive_primary_pairs}")
    
    return list(active_symbols_to_check), inactive_primary_pairs
    
