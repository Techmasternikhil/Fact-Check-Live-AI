from typing import List, Dict, Optional, Union

def calculate_average(numbers: List[Union[int, float]]) -> float:
    """Calculates the average of a list of numbers."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)

def find_user(users: List[Dict], user_id: int) -> Optional[Dict]:
    """Finds a user in a list of user dictionaries by their ID."""
    for user in users:
        if user.get('id') == user_id:
            return user
    return None

def process_data(data: Union[int, float]) -> Optional[float]:
    """Divides 100 by the provided data, handling potential errors."""
    try:
        return 100 / data
    except (ZeroDivisionError, TypeError) as e:
        print(f"Error processing data: {e}")
        return None
