"""
Retry utilities with exponential backoff for HTTP requests
"""
import asyncio
import random
from typing import Callable, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


async def retry_with_exponential_backoff(
    func: Callable,
    *args,
    retry_config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Retry a function with exponential backoff
    
    Args:
        func: The async function to retry
        *args: Arguments to pass to the function
        retry_config: Retry configuration
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        The result of the function call
        
    Raises:
        Exception: The last exception if all retries fail
    """
    if retry_config is None:
        retry_config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(retry_config.max_retries + 1):
        try:
            logger.info(f"Attempt {attempt + 1}/{retry_config.max_retries + 1}")
            result = await func(*args, **kwargs)
            if attempt > 0:
                logger.info(f"Function succeeded on attempt {attempt + 1}")
            return result
        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            
            if attempt == retry_config.max_retries:
                logger.error(f"All {retry_config.max_retries + 1} attempts failed")
                break
            
            # Calculate delay with exponential backoff
            delay = retry_config.base_delay * (retry_config.exponential_base ** attempt)
            delay = min(delay, retry_config.max_delay)
            
            # Add jitter to prevent thundering herd
            if retry_config.jitter:
                delay *= (0.5 + random.random() * 0.5)
            
            logger.info(f"Waiting {delay:.2f} seconds before retry")
            await asyncio.sleep(delay)
    
    # If we get here, all retries failed
    raise last_exception


def create_retry_config(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> RetryConfig:
    """Create a retry configuration with sensible defaults"""
    return RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter
    )
