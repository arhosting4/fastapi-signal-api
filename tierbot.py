# filename: tierbot.py

def get_tier(confidence: float, risk_status: str) -> str:
    """
    فراہم کردہ اعتماد کے اسکور اور رسک کی حالت کی بنیاد پر سگنل کا درجہ (Tier) متعین کرتا ہے۔
    
    درجہ بندی کا نظام:
    - Tier 1 (Elite): سب سے زیادہ اعتماد، کم رسک۔
    - Tier 2 (Strong): مضبوط اعتماد۔
    - Tier 3 (Moderate): قابل قبول اعتماد، معیاری سگنل۔
    - Tier 4 (Caution): کم اعتماد، احتیاط کی ضرورت۔
    - Tier 5 (Critical/Weak): انتہائی رسک یا بہت کم اعتماد، نظر انداز کیا جانا چاہیے۔

    Args:
        confidence (float): سگنل کا اعتماد کا اسکور (0-100)۔
        risk_status (str): مارکیٹ کی رسک کی حالت ("Normal", "High", "Critical")۔
        
    Returns:
        str: سگنل کا درجہ۔
    """
    # سب سے پہلے سب سے اہم حالت کو چیک کریں: انتہائی رسک
    if risk_status == "Critical":
        return "Tier 5 – Critical Risk"
    
    # اعتماد کی بنیاد پر درجہ بندی کریں
    if confidence >= 90:
        return "Tier 1 – Elite"
    elif confidence >= 80:
        return "Tier 2 – Strong"
    elif confidence >= 70:
        return "Tier 3 – Moderate"
    elif confidence >= 60:
        return "Tier 4 – Caution"
    else:
        return "Tier 5 – Weak"```

جب آپ تیار ہوں تو "next" لکھیں۔
