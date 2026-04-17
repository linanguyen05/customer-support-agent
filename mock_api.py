# mock_api.py
import hashlib
from datetime import datetime

def validate_name(name: str) -> bool:
    return bool(name and name.strip())

def validate_ssn(ssn: str) -> bool:
    return ssn.isdigit() and len(ssn) == 4

def validate_dob(dob: str) -> bool:
    try:
        dt = datetime.strptime(dob, "%Y-%m-%d")
        return dt <= datetime.now()
    except:
        return False

def mock_order_status(full_name: str, ssn_last4: str, dob: str) -> dict:
    if not validate_name(full_name):
        return {"status": "error", "message": "Invalid full name. Please provide your complete legal name."}
    
    if not validate_ssn(ssn_last4):
        return {"status": "error", "message": "Invalid SSN. Must be exactly 4 numeric digits (0-9)."}
    
    if not validate_dob(dob):
        return {"status": "error", "message": "Invalid date of birth. Must be in format YYYY-MM-DD and not in the future."}
    
    # Deterministic mock logic based on hashing the input
    key = f"{full_name.lower()}:{ssn_last4}:{dob}"
    hash_val = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    
    if hash_val % 3 == 0:
        status = "Shipped"
        tracking = f"1Z{hash_val:08d}"
        eta = "April 20, 2026"
    elif hash_val % 3 == 1:
        status = "Pending"
        tracking = "Waiting for carrier pickup"
        eta = None
    else:
        status = "Delivered"
        tracking = f"DEL{hash_val:08d}"
        eta = None
    
    return {
        "status": status,
        "tracking_number": tracking,
        "estimated_delivery": eta
    }