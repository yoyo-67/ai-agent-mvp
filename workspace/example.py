"""Example Python file for testing the AI agent.
This script provides a simple demonstration of multiple functions and a class in Python.
Each part includes docstrings or inline comments to explain its purpose."""


# Function to generate a greeting message
# Takes a name as parameter and returns a greeting
def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"


# Function to add two numbers
# Returns the sum of the two provided integers
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


# Recursive function to calculate factorial
# Calculates the factorial of a non-negative integer n
def calculate_factorial(n: int) -> int:
    """Calculate factorial of n."""
        # Base case: factorial of 0 or 1 is 1
    if n <= 1:
        return 1
        # Recursive case: n times the factorial of (n-1)
    return n * calculate_factorial(n - 1)


# Simple Counter class to demonstrate class usage in Python
# The class allows incrementing and decrementing a counter value
class Counter:
    """A simple counter class."""

        # Initialize the counter with a starting value, default is 0
    def __init__(self, start: int = 0):
        self.value = start

        # Method to increment the counter's value
    # Increases counter by 1 and returns the new value
    def increment(self) -> int:
        """Increment the counter and return new value."""
        self.value += 1
        return self.value

        # Method to decrement the counter's value
    # Decreases counter by 1 and returns the new value
    def decrement(self) -> int:
        """Decrement the counter and return new value."""
        self.value -= 1
        return self.value


# Main execution block to display example outputs
if __name__ == "__main__":
    print(greet("World"))
    print(f"5 + 3 = {add_numbers(5, 3)}")
    print(f"5! = {calculate_factorial(5)}")
