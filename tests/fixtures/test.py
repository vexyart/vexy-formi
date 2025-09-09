# Test Python file for formatting
from typing import List, Optional
import math


def calculate_statistics(numbers: List[float]) -> dict:
    """Calculate basic statistics for a list of numbers."""
    if not numbers:
        return {}
    
    total = sum(numbers)
    count = len(numbers)
    mean = total / count
    
    # Calculate standard deviation
    variance = sum((x - mean) ** 2 for x in numbers) / count
    std_dev = math.sqrt(variance)
    
    return {
        "count": count,
        "sum": total,
        "mean": mean,
        "min": min(numbers),
        "max": max(numbers),
        "std_dev": std_dev
    }


class DataProcessor:
    """Process and analyze numeric data."""
    
    def __init__(self, data: Optional[List[float]] = None):
        self.data = data or []
    
    def add_value(self, value: float) -> None:
        """Add a value to the dataset."""
        self.data.append(value)
    
    def get_stats(self) -> dict:
        """Get statistics for current dataset."""
        return calculate_statistics(self.data)


if __name__ == "__main__":
    processor = DataProcessor([1.5, 2.7, 3.1, 4.8, 5.2])
    stats = processor.get_stats()
    print(f"Statistics: {stats}")