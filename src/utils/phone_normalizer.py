"""
Phone number normalization utilities for sync operations
"""

import re
from typing import Optional, List


class PhoneNormalizer:
    """Phone number normalization class for sync operations"""

    def __init__(self):
        pass

    def normalize_phone(self, phone: str) -> Optional[str]:
        """Normalize phone number to last 10 digits for consistent lookup"""
        return normalize_phone_number(phone)

    def _extract_phone_digits(self, phone: str) -> str:
        """Extract only digits from phone number"""
        if not phone or not isinstance(phone, str):
            return ""
        return re.sub(r"\D", "", phone)


def normalize_phone_number(phone: str) -> Optional[str]:
    """
    Normalize phone number to last 10 digits for consistent lookup

    Handles various formats:
    - +919003037804 -> 9003037804
    - "whatsapp: 919003037804" -> 9003037804
    - 9003037804 -> 9003037804
    - 919003037804 -> 9003037804
    - +1-555-123-4567 -> 5551234567 (if 10 digits)
    """
    if not phone or not isinstance(phone, str):
        return None

    # Remove all non-digit characters
    digits_only = re.sub(r"\D", "", phone)

    # If we have more than 10 digits, take the last 10
    if len(digits_only) > 10:
        return digits_only[-10:]
    elif len(digits_only) == 10:
        return digits_only
    else:
        # Less than 10 digits, return None (invalid phone number)
        return None


def extract_phone_from_data(data: dict, phone_fields: List[str]) -> Optional[str]:
    """
    Extract and normalize phone number from data using multiple possible field names

    Args:
        data: Dictionary containing the data
        phone_fields: List of field names to check for phone numbers

    Returns:
        Normalized phone number or None if not found
    """
    for field in phone_fields:
        if field in data and data[field]:
            normalized = normalize_phone_number(str(data[field]))
            if normalized:
                return normalized
    return None


def get_phone_lookup_fields(source_system: str, target_system: str) -> List[str]:
    """
    Get the appropriate phone field names for lookup based on source and target systems

    Args:
        source_system: Source system (frappe/supabase)
        target_system: Target system (frappe/supabase)

    Returns:
        List of field names to check for phone numbers
    """
    if source_system == "frappe" and target_system == "supabase":
        # Frappe to Supabase: check Frappe phone fields, map to Supabase phone field
        return ["cell_number", "mobile_no", "phone", "contact_number"]
    elif source_system == "supabase" and target_system == "frappe":
        # Supabase to Frappe: check Supabase phone field, map to Frappe phone fields
        return ["phone_number", "mobile", "phone", "contact_number"]
    else:
        # Default fallback
        return ["phone_number", "cell_number", "mobile_no", "phone", "contact_number"]


def get_email_lookup_fields(source_system: str, target_system: str) -> List[str]:
    """
    Get the appropriate email field names for lookup based on source and target systems

    Args:
        source_system: Source system (frappe/supabase)
        target_system: Target system (frappe/supabase)

    Returns:
        List of field names to check for email addresses
    """
    if source_system == "frappe" and target_system == "supabase":
        # Frappe to Supabase: check Frappe email fields, map to Supabase email field
        return ["personal_email", "company_email", "preferred_contact_email", "email"]
    elif source_system == "supabase" and target_system == "frappe":
        # Supabase to Frappe: check Supabase email field, map to Frappe email fields
        return ["email", "personal_email", "company_email"]
    else:
        # Default fallback
        return ["email", "personal_email", "company_email", "preferred_contact_email"]
