from langchain_core.tools import tool
from .services import generate_random_number as service_generate_random
from .services import check_system_status as service_check_status

@tool
def get_random_number(min_val: int = 0, max_val: int = 100) -> int:
    """
    Get a random number between min_val and max_val.
    
    Args:
        min_val: Minimum value (default 0)
        max_val: Maximum value (default 100)
    """
    return service_generate_random(min_val, max_val)

@tool
def get_system_status() -> dict:
    """
    Get current system status (mock data).
    Returns CPU usage, memory usage, and uptime.
    """
    return service_check_status()

EXAMPLE_TOOLS = [get_random_number, get_system_status]
