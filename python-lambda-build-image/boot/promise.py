"""Programmable Promise implementation for Python."""
import asyncio
from typing import Generic, TypeVar, Optional

T = TypeVar('T')

class ProgrammablePromise(Generic[T]):
    """A promise that can be resolved programmatically."""
    
    def __init__(self):
        self._future: asyncio.Future[T] = asyncio.Future()
        self._value: Optional[T] = None
    
    @property
    def promise(self) -> asyncio.Future[T]:
        """Get the underlying future."""
        return self._future
    
    def resolve(self, value: T) -> None:
        """Resolve the promise with a value."""
        if not self._future.done():
            self._future.set_result(value)
        self._value = value
    
    def reject(self, reason: Exception) -> None:
        """Reject the promise with an exception."""
        if not self._future.done():
            self._future.set_exception(reason)
    
    @property
    def value(self) -> Optional[T]:
        """Get the resolved value (if available)."""
        return self._value

