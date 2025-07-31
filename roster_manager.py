# filename: roster_manager.py

import logging
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

import database_crud as crud
from config import TRADING_PAIRS

logger = logging.getLogger(__name__)

def get_current_pair_lists() -> (List[str], List[str]):
    """
    موجودہ دن کی بنیاد پر بنیادی اور بیک اپ جوڑوں کی فہرستیں واپس کرتا ہے۔
    پیر=0, ..., اتوار=6
    """
    today = datetime.utcnow().weekday()
    
    if today >= 5:  # ہفتہ یا اتوار
        logger.debug("ویک اینڈ ٹریڈنگ جوڑے منتخب کیے جا رہے ہیں۔")
        return TRADING_PAIRS.get("WEEKEND_PRIMARY", []), TRADING_PAIRS.get("WEEKEND_BACKUP", [])
    else:  # ہفتے کا دن
        logger.debug("ہفتے کے دن کے ٹریڈنگ جوڑے منتخب کیے جا رہے ہیں۔")
        return TRADING_PAIRS.get("WEEKDAY_PRIMARY", []), TRADING_PAIRS.get("WEEKDAY_BACKUP", [])

def get_hunting_roster(db: Session) -> List[str]:
    """
    شکاری انجن (Hunter Engine) کے لیے جوڑوں کی متحرک فہرست تیار کرتا ہے۔
    یہ ہمیشہ ایک مقررہ تعداد میں جوڑے واپس کرتا ہے (بنیادی فہرست کے سائز کے برابر)،
    اور فعال سگنلز والے جوڑوں کی جگہ بیک اپ جوڑوں کو شامل کرتا ہے۔
    """
    primary_pairs, backup_pairs = get_current_pair_lists()
    
    if not primary_pairs:
        logger.warning("کنفیگریشن میں کوئی بنیادی (primary) جوڑا نہیں ملا۔")
        return []
        
    roster_size = len(primary_pairs)
    
    # ڈیٹا بیس سے تمام فعال سگنلز کی علامتیں حاصل کریں
    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    # 1. بنیادی فہرست سے وہ جوڑے چنیں جن کا سگنل فعال نہیں ہے
    available_primary = [p for p in primary_pairs if p not in active_symbols]
    
    # 2. حتمی ہنٹنگ فہرست کو دستیاب بنیادی جوڑوں سے شروع کریں
    hunting_roster = available_primary
    
    # 3. اگر فہرست کا سائز کم ہے، تو اسے بیک اپ جوڑوں سے مکمل کریں
    needed = roster_size - len(hunting_roster)
    if needed > 0:
        # بیک اپ فہرست سے وہ جوڑے چنیں جو نہ تو فعال ہیں اور نہ ہی پہلے سے فہرست میں ہیں
        available_backup = [
            p for p in backup_pairs 
            if p not in active_symbols and p not in hunting_roster
        ]
        hunting_roster.extend(available_backup[:needed])
        
    logger.info(f"🏹 شکاری روسٹر تیار: {len(hunting_roster)} جوڑے -> {hunting_roster}")
    return hunting_roster

def get_monitoring_roster(db: Session) -> List[str]:
    """
    نگران انجن (Guardian Engine) کے لیے جوڑوں کی متحرک فہرست تیار کرتا ہے۔
    اس میں بنیادی جوڑے + تمام فعال سگنلز کے جوڑے شامل ہوتے ہیں تاکہ کوئی بھی اہم
    قیمت کی اپ ڈیٹ نظر انداز نہ ہو۔
    """
    primary_pairs, _ = get_current_pair_lists()
    
    # ڈیٹا بیس سے تمام فعال سگنلز کی علامتیں حاصل کریں
    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    # سیٹ (set) کا استعمال کرکے ڈپلیکیٹ سے بچیں اور تمام ضروری جوڑوں کو اکٹھا کریں
    monitoring_set = set(primary_pairs)
    monitoring_set.update(active_symbols)
    
    monitoring_list = sorted(list(monitoring_set))
    logger.info(f"🛡️ نگرانی روسٹر تیار: {len(monitoring_list)} جوڑے -> {monitoring_list}")
    return monitoring_list
    
