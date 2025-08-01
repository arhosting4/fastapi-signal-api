import logging
from datetime import datetime
from typing import List, Tuple, Set
from sqlalchemy.orm import Session

import database_crud as crud
from config import TRADING_PAIRS

logger = logging.getLogger(__name__)

# ==============================================================================
# 📅 دن کے لحاظ سے بنیادی اور بیک اپ جوڑے منتخب کریں
# ==============================================================================
def get_current_pair_lists() -> Tuple[List[str], List[str]]:
    """
    موجودہ دن کی بنیاد پر بنیادی (primary) اور بیک اپ (backup) جوڑوں کی فہرستیں واپس کرتا ہے۔
    ہفتہ/اتوار کو WEEKEND والے جوڑے اور باقی دنوں میں WEEKDAY جوڑے استعمال ہوتے ہیں۔
    """
    today = datetime.utcnow().weekday()  # 0 = Monday, 6 = Sunday

    if today >= 5:
        return TRADING_PAIRS.get("WEEKEND_PRIMARY", []), TRADING_PAIRS.get("WEEKEND_BACKUP", [])
    else:
        return TRADING_PAIRS.get("WEEKDAY_PRIMARY", []), TRADING_PAIRS.get("WEEKDAY_BACKUP", [])

# ==============================================================================
# 🏹 سگنل شکار کے لیے متحرک جوڑوں کی فہرست تیار کریں
# ==============================================================================
def get_hunting_roster(db: Session) -> List[str]:
    """
    سگنل ہنٹنگ انجن کے لیے ایک ایسی فہرست تیار کرتا ہے جس میں موجودہ ایکٹیو سگنلز شامل نہ ہوں۔
    پہلے Primary list سے بھرا جاتا ہے، باقی جگہ Backup list سے مکمل کی جاتی ہے۔
    """

    primary_pairs, backup_pairs = get_current_pair_lists()
    roster_size = len(primary_pairs)

    # 🟠 DB سے وہ symbols حاصل کریں جن پر سگنل پہلے سے active ہیں
    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}

    # 🔹 Primary اور Backup میں سے active symbols نکال دیں
    available_primary = [p for p in primary_pairs if p not in active_symbols]
    available_backup = [p for p in backup_pairs if p not in active_symbols]

    # 🔸 Hunting roster بنائیں
    hunting_roster = available_primary

    needed = roster_size - len(hunting_roster)
    if needed > 0:
        hunting_roster.extend(available_backup[:needed])

    logger.info(f"🏹 شکاری روسٹر تیار: {hunting_roster}")
    return hunting_roster
