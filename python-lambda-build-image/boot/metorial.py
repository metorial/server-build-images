"""Metorial MCP server SDK for Python Lambda."""
from typing import Any, Callable, Dict, Optional
from mcp.server import Server
from . import config
from . import oauth as oauth_module
from . import callbacks as callbacks_module

_global_server_wrapper = None

def get_args():
  """Get configuration arguments passed to the server."""
  return config.get_args()

class ServerWrapper:
  """Wrapper around MCP Server with registration methods."""
  
  def __init__(self, mcp_server: Server, name: str, version: str):
    self.mcp_server = mcp_server
    self.name = name
    self.version = version
    self._tools = {}
    self._resources = {}
    self._prompts = {}
    
  def register_tool(
    self, 
    name: str, 
    options: Dict[str, Any],
    handler: Optional[Callable] = None
  ):
    """Register a tool with the server.
    
    Can be used as a decorator or called directly with a handler.
    
    Args:
      name: Tool name
      options: Dict with 'title', 'description', and 'inputSchema'
      handler: Optional async function that takes tool arguments and returns result
    
    Returns:
      If handler is None, returns a decorator. Otherwise returns the handler.
    
    Example as decorator:
      @server.register_tool('add', {...})
      async def add_handler(arguments):
        return {...}
    
    Example with inline handler:
      server.register_tool('add', {...}, lambda args: {...})
    """
    def decorator(func: Callable):
      self._tools[name] = {
        "options": options,
        "handler": func
      }
      return func
    
    if handler is None:
      return decorator
    else:
      return decorator(handler)
  
  def register_resource(
    self,
    name: str,
    template: Any,
    options: Dict[str, Any],
    handler: Optional[Callable] = None
  ):
    """Register a resource with the server.
    
    Can be used as a decorator or called directly with a handler.
    
    Args:
      name: Resource name
      template: Resource URI template
      options: Dict with 'title' and 'description'
      handler: Optional async function that handles resource reads
    
    Returns:
      If handler is None, returns a decorator. Otherwise returns the handler.
    """
    def decorator(func: Callable):
      self._resources[name] = {
        "template": template,
        "options": options,
        "handler": func
      }
      return func
    
    if handler is None:
      return decorator
    else:
      return decorator(handler)
  
  def register_prompt(
    self,
    name: str,
    options: Dict[str, Any],
    handler: Optional[Callable] = None
  ):
    """Register a prompt with the server.
    
    Can be used as a decorator or called directly with a handler.
    
    Args:
      name: Prompt name
      options: Dict with 'title', 'description', and optional 'arguments'
      handler: Optional async function that handles prompt generation
    
    Returns:
      If handler is None, returns a decorator. Otherwise returns the handler.
    """
    def decorator(func: Callable):
      self._prompts[name] = {
        "options": options,
        "handler": func
      }
      return func
    
    if handler is None:
      return decorator
    else:
      return decorator(handler)
  
  def set_oauth_handler(
    self,
    get_authorization_url,
    handle_callback,
    get_auth_form=None,
    refresh_access_token=None
  ):
    """Register an OAuth handler for the server."""
    if get_authorization_url is None:
      raise ValueError("get_authorization_url is required")
    if handle_callback is None:
      raise ValueError("handle_callback is required")
    
    handler = oauth_module.OAuthHandler(
      get_authorization_url=get_authorization_url,
      handle_callback=handle_callback,
      get_auth_form=get_auth_form,
      refresh_access_token=refresh_access_token
    )
    oauth_module.set_oauth(handler)
  
  def set_callback_handler(
    self,
    handle,
    install=None,
    poll=None
  ):
    """Register a callback handler for the server."""
    if handle is None:
      raise ValueError("handle is required")
    
    handler = callbacks_module.CallbackHandler(
      handle_hook=handle,
      install_hook=install,
      poll_hook=poll
    )
    callbacks_module.set_callbacks(handler)
  
  async def _list_tools(self):
    """Internal handler for listing tools."""
    tools = []
    for name, info in self._tools.items():
      tool_def = {
        "name": name,
        "description": info["options"].get("description", ""),
        "inputSchema": info["options"].get("inputSchema", {"type": "object", "properties": {}})
      }
      tools.append(tool_def)
    return tools
  
  async def _call_tool(self, name: str, arguments: dict):
    """Internal handler for calling tools."""
    if name not in self._tools:
      raise ValueError(f"Unknown tool: {name}")
    
    handler = self._tools[name]["handler"]
    return await handler(arguments)
  
  async def _list_resources(self):
    """Internal handler for listing resources."""
    resources = []
    for name, info in self._resources.items():
      template = info["template"]

      if isinstance(template, str):
        uri_template = template
      else:
        uri_template = getattr(template, 'uriTemplate', str(template))
      
      resource_def = {
        "uri": uri_template,
        "name": info["options"].get("title", name),
        "description": info["options"].get("description", ""),
        "mimeType": info["options"].get("mimeType", "text/plain")
      }
      resources.append(resource_def)
    return resources
  
  async def _read_resource(self, uri: str):
    """Internal handler for reading resources."""
    for name, info in self._resources.items():
      handler = info["handler"]

      result = await handler(uri)
      if result:
        return result
    
    raise ValueError(f"Unknown resource: {uri}")
  
  async def _list_prompts(self):
    """Internal handler for listing prompts."""
    prompts = []
    for name, info in self._prompts.items():
      prompt_def = {
        "name": name,
        "description": info["options"].get("description", ""),
      }
      if "arguments" in info["options"]:
        prompt_def["arguments"] = info["options"]["arguments"]
      prompts.append(prompt_def)
    return prompts
  
  async def _get_prompt(self, name: str, arguments: dict):
    """Internal handler for getting prompts."""
    if name not in self._prompts:
      raise ValueError(f"Unknown prompt: {name}")
    
    handler = self._prompts[name]["handler"]
    return await handler(arguments)
  
  def get_capabilities(self):
    """Get server capabilities based on registered tools/resources/prompts."""
    capabilities = {
      "experimental": {}
    }
    
    if self._tools:
      capabilities["tools"] = {
        "listChanged": False
      }
    
    if self._resources:
      capabilities["resources"] = {
        "listChanged": False,
        "subscribe": False
      }
    
    if self._prompts:
      capabilities["prompts"] = {
        "listChanged": False
      }
    
    return capabilities

def create_server(info: Dict[str, str]):
  """Create a Metorial MCP server.
  
  Args:
    info: Dict with 'name' and 'version'
  
  Returns:
    ServerWrapper instance to register tools, resources, and prompts
  
  Example:
    server = metorial.create_server({'name': 'my-server', 'version': '1.0.0'})
    
    @server.register_tool('add', {...})
    async def add_handler(arguments):
      return {...}
    
    @server.register_resource('greeting', 'greeting://{name}', {...})
    async def greeting_handler(uri):
      return {...}
  """
  global _global_server_wrapper
  
  name = info.get("name", "mcp-server")
  version = info.get("version", "1.0.0")
  
  mcp_server = Server(name)
  mcp_server.version = version
  server_wrapper = ServerWrapper(mcp_server, name, version)
  _global_server_wrapper = server_wrapper

  config.set_server(server_wrapper)
  
  return server_wrapper

def set_oauth_handler(
  get_authorization_url,
  handle_callback,
  get_auth_form=None,
  refresh_access_token=None
):
  """Register an OAuth handler at module level."""
  if get_authorization_url is None:
    raise ValueError("get_authorization_url is required")
  if handle_callback is None:
    raise ValueError("handle_callback is required")
  
  handler = oauth_module.OAuthHandler(
    get_authorization_url=get_authorization_url,
    handle_callback=handle_callback,
    get_auth_form=get_auth_form,
    refresh_access_token=refresh_access_token
  )
  oauth_module.set_oauth(handler)

def set_callback_handler(
  handle,
  install=None,
  poll=None
):
  """Register a callback handler at module level."""
  if handle is None:
    raise ValueError("handle is required")
  
  handler = callbacks_module.CallbackHandler(
    handle_hook=handle,
    install_hook=install,
    poll_hook=poll
  )
  callbacks_module.set_callbacks(handler)

__all__ = [
  'create_server',
  'get_args',
  'set_oauth_handler',
  'set_callback_handler'
]
