def mask_pan(pan: str) -> str:
    """Mask PAN to ****XXXX format (last 4 characters visible)."""
    if not pan or len(pan) < 4:
        return pan
    return f"****{pan[-4:]}"

def mask_account_number(acc_num: str) -> str:
    """Mask bank account number to ****XXXX format (last 4 digits visible)."""
    if not acc_num or len(acc_num) < 4:
        return acc_num
    return f"****{acc_num[-4:]}"

def mask_kyc_record(kyc_data: dict) -> dict:
    """Return a copy of KYC record with PII masked as ****XXXX."""
    if not kyc_data:
        return {}
    masked = dict(kyc_data)
    if "pan" in masked:
        masked["pan"] = mask_pan(str(masked["pan"]))
    if "bank_account" in masked and isinstance(masked["bank_account"], dict):
        bank_acc = dict(masked["bank_account"])
        if "account_number" in bank_acc:
            bank_acc["account_number"] = mask_account_number(str(bank_acc["account_number"]))
        masked["bank_account"] = bank_acc
    return masked
