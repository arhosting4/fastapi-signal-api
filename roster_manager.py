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
        primary = TRADING_PAIRS.get("WEEKEND_PRIMARY", [])
        backup = TRADING_PAIRS.get("WEEKEND_BACKUP", [])
        return primary, backup
    else:  # ہفتے کا دن
        primary = TRADING_PAIRS.get("WEEKDAY_PRIMARY", [])
        backup = TRADING_PAIRS.get("WEEKDAY_BACKUP", [])
        return primary, backup

def get_hunting_roster(db: Session) -> List[str]:
    """
    شکاری انجن کے لیے جوڑوں کی متحرک فہرست تیار کرتا ہے۔
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
        
    logger.info(f"شکاری روسٹر تیار: {hunting_roster}")
    return hunting_roster

# ★★★ یہاں تبدیلی کی گئی ہے - یہ اب مکمل طور پر درست ہے ★★★
def get_monitoring_roster(db: Session) -> List[str]:
    """
    نگران انجن کے لیے جوڑوں کی حتمی فہرست تیار کرتا ہے۔
    یہ یقینی بناتا ہے کہ تمام فعال سگنلز کی نگرانی کی جائے۔
    """
    # 1. موجودہ دن کے تمام ممکنہ جوڑوں کو حاصل کریں (بنیادی + بیک اپ)
    primary_pairs, backup_pairs = get_current_pair_lists()
    all_possible_pairs = set(primary_pairs + backup_pairs)
    
    # 2. تمام فعال سگنلز کے جوڑوں کو حاصل کریں
    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    # 3. ان دونوں سیٹوں کو ملا دیں تاکہ کوئی بھی جوڑا چھوٹ نہ جائے
    monitoring_set = all_possible_pairs.union(active_symbols)
    
    monitoring_list = sorted(list(monitoring_set))
    logger.info(f"نگرانی روسٹر تیار (تمام فعال سگنلز سمیت): {monitoring_list}")
    return monitoring_list
    
