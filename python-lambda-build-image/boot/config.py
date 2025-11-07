"""Configuration management for Metorial MCP servers."""
from .promise import ProgrammablePromise
from typing import Any, Dict

# Create isolated promise instances for each scope
current_oauth = ProgrammablePromise()
current_server = ProgrammablePromise()
current_hook = ProgrammablePromise()
current_args = ProgrammablePromise()

def set_mcp_auth(value: Any) -> None:
    """Set the OAuth authentication handler."""
    current_oauth.resolve(value)

def get_mcp_auth() -> Any:
    """Get the OAuth authentication handler promise."""
    return current_oauth.promise

def set_server(value: Any) -> None:
    """Set the MCP server instance."""
    current_server.resolve(value)

def get_server() -> Any:
    """Get the MCP server instance promise."""
    return current_server.promise

def set_callback_handler(value: Any) -> None:
    """Set the callback handler."""
    current_hook.resolve(value)

def get_callback_handler() -> Any:
    """Get the callback handler promise."""
    return current_hook.promise

def set_args(args: Dict[str, Any]) -> None:
    """Set the configuration arguments."""
    current_args.resolve(args)

def get_args() -> Dict[str, Any]:
    """Get the configuration arguments (synchronously, returns resolved value or empty dict)."""
    return current_args.value if current_args.value is not None else {}

def reset_all() -> None:
    """Reset all promises for a new invocation context."""
    global current_oauth, current_server, current_hook, current_args
    current_oauth = ProgrammablePromise()
    current_server = ProgrammablePromise()
    current_hook = ProgrammablePromise()
    current_args = ProgrammablePromise()
