"""Configuration management for Metorial MCP servers using contextvars."""
from contextvars import ContextVar
from typing import Any, Dict, Optional

# Create context variables for per-invocation isolation
current_oauth: ContextVar[Optional[Any]] = ContextVar('current_oauth', default=None)
current_server: ContextVar[Optional[Any]] = ContextVar('current_server', default=None)
current_hook: ContextVar[Optional[Any]] = ContextVar('current_hook', default=None)
current_args: ContextVar[Dict[str, Any]] = ContextVar('current_args', default={})

def set_mcp_auth(value: Any) -> None:
    """Set the OAuth authentication handler."""
    current_oauth.set(value)

def get_mcp_auth() -> Optional[Any]:
    """Get the OAuth authentication handler."""
    return current_oauth.get()

def set_server(value: Any) -> None:
    """Set the MCP server instance."""
    current_server.set(value)

def get_server() -> Optional[Any]:
    """Get the MCP server instance."""
    return current_server.get()

def set_callback_handler(value: Any) -> None:
    """Set the callback handler."""
    current_hook.set(value)

def get_callback_handler() -> Optional[Any]:
    """Get the callback handler."""
    return current_hook.get()

def set_args(args: Dict[str, Any]) -> None:
    """Set the configuration arguments."""
    current_args.set(args)

def get_args() -> Dict[str, Any]:
    """Get the configuration arguments."""
    return current_args.get()
