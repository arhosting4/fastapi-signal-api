# filename: roster_manager.py

import logging
from datetime import datetime
from typing import List, Tuple
from sqlalchemy.orm import Session

import database_crud as crud
from config import TRADING_PAIRS

logger = logging.getLogger(__name__)

def get_current_pair_lists() -> Tuple[List[str], List[str]]:
    """موجودہ دن کی بنیاد پر بنیادی اور بیک اپ جوڑوں کی فہرستیں واپس کرتا ہے۔"""
    today = datetime.utcnow().weekday()  # پیر=0, ..., اتوار=6
    
    if today >= 5:  # ہفتہ یا اتوار
        return TRADING_PAIRS.get("WEEKEND_PRIMARY", []), TRADING_PAIRS.get("WEEKEND_BACKUP", [])
    else:  # ہفتے کا دن
        return TRADING_PAIRS.get("WEEKDAY_PRIMARY", []), TRADING_PAIRS.get("WEEKDAY_BACKUP", [])

def get_hunting_roster(db: Session) -> List[str]:
    """
    شکاری انجن کے لیے جوڑوں کی متحرک فہرست تیار کرتا ہے۔
    یہ ہمیشہ ایک مقررہ تعداد میں جوڑے واپس کرتا ہے۔
    """
    primary_pairs, backup_pairs = get_current_pair_lists()
    roster_size = len(primary_pairs)
    
    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    available_primary = [p for p in primary_pairs if p not in active_symbols]
    available_backup = [p for p in backup_pairs if p not in active_symbols]
    
    hunting_roster = available_primary
    
    needed = roster_size - len(hunting_roster)
    if needed > 0:
        hunting_roster.extend(available_backup[:needed])
        
    logger.info(f"🏹 شکاری روسٹر تیار: {hunting_roster}")
    return hunting_roster

# ★★★ مکمل طور پر نیا اور ذہین فنکشن ★★★
def get_split_monitoring_roster(db: Session) -> Tuple[List[str], List[str]]:
    """
    نگرانی کی فہرست کو دو حصوں میں تقسیم کرتا ہے:
    1.  فعال سگنلز والی علامتیں (جن کے لیے /time_series استعمال ہوگا)
    2.  باقی اہم علامتیں (جن کے لیے /quote استعمال ہوگا)
    
    Returns:
        Tuple[List[str], List[str]]: (active_signal_symbols, inactive_primary_symbols)
    """
    # 1. تمام فعال سگنلز کی علامتیں حاصل کریں
    active_signal_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    # 2. آج کے لیے بنیادی جوڑوں کی فہرست حاصل کریں
    primary_pairs, _ = get_current_pair_lists()
    
    # 3. بنیادی جوڑوں میں سے ان کو الگ کریں جن کا سگنل فعال نہیں ہے
    inactive_primary_symbols = [p for p in primary_pairs if p not in active_signal_symbols]
    
    # 4. دونوں فہرستوں کو واپس کریں
    active_list = sorted(list(active_signal_symbols))
    inactive_list = sorted(inactive_primary_symbols)
    
    logger.info(f"🛡️ تقسیم شدہ نگرانی روسٹر تیار:")
    logger.info(f"   - درست جانچ کے لیے (فعال سگنلز): {active_list}")
    logger.info(f"   - قیمت اپ ڈیٹ کے لیے (غیر فعال): {inactive_list}")
    
    return active_list, inactive_list

# یہ پرانا فنکشن اب استعمال نہیں ہوگا، لیکن ہم اسے رکھ سکتے ہیں اگر کوئی اور حصہ اسے استعمال کر رہا ہو
def get_monitoring_roster(db: Session) -> List[str]:
    """
    نگران انجن کے لیے جوڑوں کی ایک متحدہ فہرست تیار کرتا ہے۔
    نوٹ: یہ فنکشن اب get_split_monitoring_roster کے حق میں متروک ہو رہا ہے۔
    """
    primary_pairs, _ = get_current_pair_lists()
    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    monitoring_set = set(primary_pairs)
    monitoring_set.update(active_symbols)
    monitoring_list = sorted(list(monitoring_set))
    logger.info(f"نگرانی روسٹر تیار: {monitoring_list}")
    return monitoring_list
    
