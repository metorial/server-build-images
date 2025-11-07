"""Programmable Promise implementation for Python."""
from typing import Generic, TypeVar, Optional

T = TypeVar('T')

class ProgrammablePromise(Generic[T]):
    """A promise-like container that can be resolved programmatically."""
    
    def __init__(self):
        self._value: Optional[T] = None
        self._resolved: bool = False
    
    @property
    def promise(self) -> 'ProgrammablePromise[T]':
        """Get the promise itself."""
        return self
    
    def resolve(self, value: T) -> None:
        """Resolve the promise with a value."""
        self._value = value
        self._resolved = True
    
    def reject(self, reason: Exception) -> None:
        """Reject the promise with an exception."""
        self._resolved = False
    
    @property
    def value(self) -> Optional[T]:
        """Get the resolved value (if available)."""
        return self._value
    
    @property
    def resolved(self) -> bool:
        """Check if the promise has been resolved."""
        return self._resolved
