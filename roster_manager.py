# filename: roster_manager.py

import logging
from datetime import datetime
from typing import List, Tuple, Set
from sqlalchemy.orm import Session

import database_crud as crud
from config import TRADING_PAIRS

logger = logging.getLogger(__name__)

def get_current_pair_lists() -> Tuple[List[str], List[str]]:
    """
    آج کے دن کے حساب سے پرائمری اور بیک اپ trading pairs کی فہرستیں واپس کرے۔
    صرف config.py سے centralized لئے جاتے ہیں (کوئی تضاد ممکن نہیں)۔
    """
    today = datetime.utcnow().weekday()  # 0=Monday ... 6=Sunday
    if today >= 5:
        return TRADING_PAIRS.get("WEEKEND_PRIMARY", []), TRADING_PAIRS.get("WEEKEND_BACKUP", [])
    else:
        return TRADING_PAIRS.get("WEEKDAY_PRIMARY", []), TRADING_PAIRS.get("WEEKDAY_BACKUP", [])

def get_hunting_roster(db: Session) -> List[str]:
    """
    آج کے دن کا شکاری روسٹر بناتا ہے:
    - active signals (DB سے) نکال کر باقی primaries/backup سے dynamic prioritized pair list
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

def get_split_monitoring_roster(db: Session, active_symbols_to_check: Set[str]) -> Tuple[List[str], List[str]]:
    """
    موجودہ primary pairs میں سے:
    - جن پر active signal ہے (DB سے ملتے)، وہ precise monitoring (e.g. OHLC/TP/SL) کے لیے لوٹائیں
    - باقی primary مگر غیر فعال: صرف quick quote check/update کے لیے
    """
    primary_pairs, _ = get_current_pair_lists()
    inactive_primary_pairs = [p for p in primary_pairs if p not in active_symbols_to_check]
    logger.info("🛡️ تقسیم شدہ نگرانی روسٹر تیار:")
    logger.info(f" - درست جانچ کے لیے (فعال سگنلز): {list(active_symbols_to_check)}")
    logger.info(f" - قیمت اپ ڈیٹ کے لیے (غیر فعال): {inactive_primary_pairs}")
    return list(active_symbols_to_check), inactive_primary_pairs
    
