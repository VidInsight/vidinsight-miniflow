"""Datetime formatting utilities to eliminate timestamp duplication."""

from datetime import datetime
from typing import Dict, List, Optional, Any

def format_timestamp_fields(obj: Any, fields: List[str] = None) -> Dict[str, Optional[str]]:
    """Convert datetime fields to ISO format with None handling."""
    if fields is None:
        fields = ['started_at', 'ended_at', 'created_at', 'updated_at']
    
    result = {}
    for field in fields:
        value = getattr(obj, field, None)
        result[field] = value.isoformat() if value else None
    
    return result

def current_timestamp() -> str:
    """Get current UTC timestamp in ISO format with Z suffix."""
    return datetime.utcnow().isoformat() + "Z"

def format_single_timestamp(timestamp: Optional[datetime]) -> Optional[str]:
    """Format a single datetime to ISO string with None handling."""
    return timestamp.isoformat() if timestamp else None

# format_model_timestamps function removed - was unused