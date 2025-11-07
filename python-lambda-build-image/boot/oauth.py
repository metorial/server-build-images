"""OAuth handling for Metorial MCP servers."""
from typing import Any, Dict, Optional, Callable
import inspect
import asyncio

from . import config

async def _call_handler(handler: Callable, *args, **kwargs):
    """Call handler supporting both sync and async functions."""
    if inspect.iscoroutinefunction(handler):
        return await handler(*args, **kwargs)
    else:
        result = handler(*args, **kwargs)
        # If result is a coroutine, await it
        if inspect.iscoroutine(result):
            return await result
        return result

class OAuthHandler:
    """OAuth handler interface."""
    
    def __init__(self,
                 get_authorization_url: Callable,
                 handle_callback: Callable,
                 get_auth_form: Optional[Callable] = None,
                 refresh_access_token: Optional[Callable] = None):
        self.get_authorization_url = get_authorization_url
        self.handle_callback = handle_callback
        self.get_auth_form = get_auth_form
        self.refresh_access_token = refresh_access_token

def set_oauth(handler: OAuthHandler):
    """Register the OAuth handler."""
    config.set_mcp_auth(handler)

async def get_oauth() -> Optional[OAuthHandler]:
    """Get the registered OAuth handler with timeout."""
    try:
        oauth_promise = config.get_mcp_auth()
        result = await asyncio.wait_for(oauth_promise, timeout=0.5)
        return result
    except asyncio.TimeoutError:
        return None

async def handle_oauth_get() -> Dict[str, Any]:
    """Handle OAuth get request."""
    oauth = await get_oauth()
    if not oauth:
        return {"enabled": False, "hasForm": False}
    return {"enabled": True, "hasForm": oauth.get_auth_form is not None}

async def handle_oauth_authorization_url(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle OAuth authorization URL request."""
    oauth = await get_oauth()
    if not oauth:
        raise ValueError("OAuth not configured")
    
    result = await _call_handler(oauth.get_authorization_url, input_data)
    if isinstance(result, str):
        return {"authorizationUrl": result, "codeVerifier": ""}
    return result

async def handle_oauth_authorization_form(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle OAuth authorization form request."""
    oauth = await get_oauth()
    if not oauth or not oauth.get_auth_form:
        raise ValueError("OAuth form not available")
    
    form = await _call_handler(oauth.get_auth_form, input_data)
    return {"authForm": form}

async def handle_oauth_callback(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle OAuth callback request."""
    oauth = await get_oauth()
    if not oauth:
        raise ValueError("OAuth not configured")
    
    auth_data = await _call_handler(oauth.handle_callback, input_data)
    return {"authData": auth_data}

async def handle_oauth_refresh(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle OAuth token refresh request."""
    oauth = await get_oauth()
    if not oauth or not oauth.refresh_access_token:
        raise ValueError("OAuth refresh not supported")
    
    auth_data = await _call_handler(oauth.refresh_access_token, input_data)
    return {"authData": auth_data}
