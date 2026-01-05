TRUST_THRESHOLD = 0.0   # tune empirically

def decision(trust_score):
    if trust_score >= TRUST_THRESHOLD:
        return True   # ACCEPT
    else:
        return False  # REJECT
