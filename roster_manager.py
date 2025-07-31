# filename: roster_manager.py

import logging
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

import database_crud as crud
from config import TRADING_PAIRS

logger = logging.getLogger(__name__)

def get_current_pair_lists() -> (List[str], List[str]):
    """موجودہ دن کی بنیاد پر بنیادی اور بیک اپ جوڑوں کی فہرستیں واپس کرتا ہے۔"""
    today = datetime.utcnow().weekday()  # پیر=0, ..., اتوار=6
    
    if today >= 5:  # ہفتہ یا اتوار
        return TRADING_PAIRS["WEEKEND_PRIMARY"], TRADING_PAIRS["WEEKEND_BACKUP"]
    else:  # ہفتے کا دن
        return TRADING_PAIRS["WEEKDAY_PRIMARY"], TRADING_PAIRS["WEEKDAY_BACKUP"]

def get_hunting_roster(db: Session) -> List[str]:
    """
    شکاری انجن کے لیے جوڑوں کی متحرک فہرست تیار کرتا ہے۔
    یہ ہمیشہ ایک مقررہ تعداد میں جوڑے واپس کرتا ہے (بنیادی فہرست کے سائز کے برابر)۔
    """
    primary_pairs, backup_pairs = get_current_pair_lists()
    roster_size = len(primary_pairs)
    
    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    # 1. بنیادی فہرست سے وہ جوڑے چنیں جن کا سگنل فعال نہیں ہے
    available_primary = [p for p in primary_pairs if p not in active_symbols]
    
    # 2. بیک اپ فہرست سے وہ جوڑے چنیں جن کا سگنل فعال نہیں ہے
    available_backup = [p for p in backup_pairs if p not in active_symbols]
    
    # 3. حتمی فہرست بنائیں
    hunting_roster = available_primary
    
    # 4. اگر ضرورت ہو تو بیک اپ جوڑوں سے فہرست مکمل کریں
    needed = roster_size - len(hunting_roster)
    if needed > 0:
        hunting_roster.extend(available_backup[:needed])
        
    logger.info(f"شکاری روسٹر تیار: {hunting_roster}")
    return hunting_roster

def get_monitoring_roster(db: Session) -> List[str]:
    """
    نگران انجن کے لیے جوڑوں کی متحرک فہرست تیار کرتا ہے۔
    اس میں بنیادی جوڑے + تمام فعال سگنلز کے جوڑے شامل ہوتے ہیں۔
    """
    primary_pairs, _ = get_current_pair_lists()
    
    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    # سیٹ کا استعمال کرکے ڈپلیکیٹ سے بچیں
    monitoring_set = set(primary_pairs)
    monitoring_set.update(active_symbols)
    
    monitoring_list = sorted(list(monitoring_set))
    logger.info(f"نگرانی روسٹر تیار: {monitoring_list}")
    return monitoring_list
