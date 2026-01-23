import random
from typing import Dict, Any, Optional
from .models import ExampleItem

def generate_random_number(min_val: int = 0, max_val: int = 100) -> int:
    """
    Generate a random number and log it to the database.
    """
    value = random.randint(min_val, max_val)
    
    # Log to DB
    ExampleItem.objects.create(
        name="Random Number",
        value=str(value),
        item_type="random"
    )
    
    return value

def check_system_status() -> Dict[str, Any]:
    """
    Check system status and log it.
    """
    status_data = {
        "cpu_usage": f"{random.randint(10, 80)}%",
        "memory_usage": f"{random.randint(20, 90)}%",
        "uptime": "99.9%",
        "status": "healthy"
    }
    
    # Log to DB
    ExampleItem.objects.create(
        name="System Status",
        value=str(status_data),
        item_type="system"
    )
    
    return status_data

def get_recent_items(limit: int = 10):
    """
    Get recent example items.
    """
    return ExampleItem.objects.all()[:limit]
