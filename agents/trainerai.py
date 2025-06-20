def get_confidence(pair, tf, core, pattern):
    base = 75
    if pattern['confidence'] > 0.80:
        base += 10
    if core['signal'] == "BUY":
        base += 2
    return min(base, 99)