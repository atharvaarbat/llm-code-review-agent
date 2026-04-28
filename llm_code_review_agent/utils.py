import time
import functools
import random
from typing import Callable, Any

def retry_with_backoff(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
):
    """
    Decorator that retries a function with exponential backoff.
    Catches all exceptions; stops after max_retries.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries:
                        raise
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    if jitter:
                        delay *= random.uniform(0.5, 1.5)
                    time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

class Timer:
    """Context manager for measuring elapsed time."""
    def __init__(self, description: str = "Operation"):
        self.description = description
        self.start = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        elapsed = time.perf_counter() - self.start
        print(f"[TIMER] {self.description}: {elapsed:.3f}s", flush=True)