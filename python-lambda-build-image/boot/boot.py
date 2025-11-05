"""Bootstrap module for Metorial Python Lambda handlers."""
import asyncio
import json
import sys
import os
import importlib.util
import builtins
from typing import Any, Dict, Optional
from io import StringIO

from mcp.server.lowlevel.server import NotificationOptions

from . import config
from . import oauth
from . import callbacks

_user_module_loaded = False
_server = None
_handlers = {}

class LogCapture:
  """Captures stdout/stderr for log instrumentation."""
  
  def __init__(self):
    self.logs = []
    self.original_stdout = None
    self.original_stderr = None
    self.stdout_capture = None
    self.stderr_capture = None
  
  def start(self):
    """Start capturing output."""
    self.original_stdout = sys.stdout
    self.original_stderr = sys.stderr
    self.stdout_capture = StringIO()
    self.stderr_capture = StringIO()
    sys.stdout = self.stdout_capture
    sys.stderr = self.stderr_capture
  
  def stop(self):
    """Stop capturing and collect logs."""
    if self.original_stdout:
      sys.stdout = self.original_stdout
    if self.original_stderr:
      sys.stderr = self.original_stderr
    
    if self.stdout_capture:
      stdout_text = self.stdout_capture.getvalue()
      if stdout_text.strip():
        self.logs.append({
          "type": "info",
          "lines": stdout_text.strip().split('\n')
        })
    
    if self.stderr_capture:
      stderr_text = self.stderr_capture.getvalue()
      if stderr_text.strip():
        self.logs.append({
          "type": "error",
          "lines": stderr_text.strip().split('\n')
        })
    
    return self.logs

def load_user_server(args: Dict[str, Any]):
  global _user_module_loaded, _server, _handlers
  
  config.set_args(args)
  
  if not _user_module_loaded:
    entrypoint = os.environ.get('METORIAL_ENTRYPOINT', 'server.py')
    
    module_name = entrypoint.replace('.py', '').replace('/', '.')
    spec = importlib.util.spec_from_file_location(module_name, entrypoint)
    if spec and spec.loader:
      module = importlib.util.module_from_spec(spec)
      sys.modules[module_name] = module
      spec.loader.exec_module(module)
      _user_module_loaded = True
  
  _server = getattr(builtins, '__metorial_server__', None)
  if _server is None:
    raise RuntimeError("No MCP server found. Did you call metorial.create_server()?")
  
  _handlers = getattr(builtins, '__metorial_handlers__', {})
  
  return _server, _handlers

async def handle_discover(event: Dict[str, Any]) -> Dict[str, Any]:
  try:
    args = event.get('args', {})
    server, handlers = load_user_server(args)
    
    tools = []
    resource_templates = []
    prompts = []
    
    if 'list_tools' in handlers:
      tools_result = await handlers['list_tools']()
      if tools_result:
        tools = tools_result if isinstance(tools_result, list) else []
    
    if 'list_resources' in handlers:
      resources_result = await handlers['list_resources']()
      if resources_result:
        resource_templates = resources_result if isinstance(resources_result, list) else []
    
    if 'list_prompts' in handlers:
      prompts_result = await handlers['list_prompts']()
      if prompts_result:
        prompts = prompts_result if isinstance(prompts_result, list) else []
    
    # Get server capabilities
    notification_options = getattr(server, 'notification_options', NotificationOptions())
    server_capabilities = server.get_capabilities(notification_options, {})
    
    return {
      "success": True,
      "discovery": {
        "tools": tools,
        "resourceTemplates": resource_templates,
        "prompts": prompts,
        "capabilities": server_capabilities.model_dump(exclude_none=True),
        "implementation": {
          "name": server.name if hasattr(server, 'name') else "unknown",
          "version": server.version if hasattr(server, 'version') else "1.0.0"
        },
        "instructions": None
      }
    }
  except Exception as e:
    import traceback
    return {
      "success": False,
      "error": {
        "code": "discovery_error",
        "message": str(e) + "\n" + traceback.format_exc()
      }
    }

async def handle_mcp_request(event: Dict[str, Any]) -> Dict[str, Any]:
  """Handle MCP requests by directly calling handlers."""
  try:
    args_raw = event.get('args', '{}')
    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
    
    server, handlers = load_user_server(args)
    
    messages_raw = event.get('messages', [])
    
    responses = []
    
    for message_raw in messages_raw:
      message = json.loads(message_raw) if isinstance(message_raw, str) else message_raw
      
      try:
        method = message.get('method')
        params = message.get('params', {})
        
        if 'id' not in message:
          continue
        
        if method == 'initialize':
          notification_options = getattr(server, 'notification_options', NotificationOptions())
          server_capabilities = server.get_capabilities(notification_options, {})
          
          responses.append({
            "jsonrpc": "2.0",
            "id": message['id'],
            "result": {
              "protocolVersion": params.get('protocolVersion', '2024-11-05'),
              "capabilities": server_capabilities.model_dump(exclude_none=True),
              "serverInfo": {
                "name": server.name if hasattr(server, 'name') else "unknown",
                "version": server.version if hasattr(server, 'version') else "1.0.0"
              }
            }
          })
        
        elif method == 'tools/list':
          if 'list_tools' in handlers:
            tools = await handlers['list_tools']()
            responses.append({
              "jsonrpc": "2.0",
              "id": message['id'],
              "result": {"tools": tools if tools else []}
            })
          else:
            responses.append({
              "jsonrpc": "2.0",
              "id": message['id'],
              "result": {"tools": []}
            })
        
        elif method == 'tools/call':
          if 'call_tool' in handlers:
            name = params.get('name')
            arguments = params.get('arguments', {})
            result = await handlers['call_tool'](name, arguments)
            responses.append({
              "jsonrpc": "2.0",
              "id": message['id'],
              "result": result
            })
          else:
            raise ValueError("call_tool handler not registered")
        
        elif method == 'resources/list':
          if 'list_resources' in handlers:
            resources = await handlers['list_resources']()
            responses.append({
              "jsonrpc": "2.0",
              "id": message['id'],
              "result": {"resources": resources if resources else []}
            })
          else:
            responses.append({
              "jsonrpc": "2.0",
              "id": message['id'],
              "result": {"resources": []}
            })
        
        elif method == 'resources/read':
          if 'read_resource' in handlers:
            uri = params.get('uri')
            result = await handlers['read_resource'](uri)
            responses.append({
              "jsonrpc": "2.0",
              "id": message['id'],
              "result": result
            })
          else:
            raise ValueError("read_resource handler not registered")
        
        elif method == 'prompts/list':
          if 'list_prompts' in handlers:
            prompts = await handlers['list_prompts']()
            responses.append({
              "jsonrpc": "2.0",
              "id": message['id'],
              "result": {"prompts": prompts if prompts else []}
            })
          else:
            responses.append({
              "jsonrpc": "2.0",
              "id": message['id'],
              "result": {"prompts": []}
            })
        
        elif method == 'prompts/get':
          if 'get_prompt' in handlers:
            name = params.get('name')
            arguments = params.get('arguments', {})
            result = await handlers['get_prompt'](name, arguments)
            responses.append({
              "jsonrpc": "2.0",
              "id": message['id'],
              "result": result
            })
          else:
            raise ValueError("get_prompt handler not registered")
        
        elif method == 'ping':
          responses.append({
            "jsonrpc": "2.0",
            "id": message['id'],
            "result": {}
          })
        
        else:
          responses.append({
            "jsonrpc": "2.0",
            "id": message['id'],
            "error": {
              "code": -32601,
              "message": f"Method not found: {method}"
            }
          })
      
      except Exception as e:
        import traceback
        responses.append({
          "jsonrpc": "2.0",
          "id": message.get('id'),
          "error": {
            "code": -32603,
            "message": str(e),
            "data": traceback.format_exc()
          }
        })
    
    await asyncio.sleep(0.1)
    
    return {
      "success": True,
      "responses": responses
    }
  except Exception as e:
    import traceback
    return {
      "success": False,
      "error": {
        "code": "mcp_error",
        "message": str(e) + "\n" + traceback.format_exc()
      }
    }

async def handle_oauth_action(event: Dict[str, Any]) -> Dict[str, Any]:
  try:
    load_user_server({})
    
    oauth_action = event.get('oauthAction')
    oauth_input = event.get('oauthInput', {})
    
    if oauth_action == 'get':
      result = await oauth.handle_oauth_get()
      return {"success": True, "oauth": result}
    elif oauth_action == 'authorization-url':
      result = await oauth.handle_oauth_authorization_url(oauth_input)
      return {"success": True, "oauth": result}
    elif oauth_action == 'authorization-form':
      result = await oauth.handle_oauth_authorization_form(oauth_input)
      return {"success": True, "oauth": result}
    elif oauth_action == 'callback':
      result = await oauth.handle_oauth_callback(oauth_input)
      return {"success": True, "oauth": result}
    elif oauth_action == 'refresh':
      result = await oauth.handle_oauth_refresh(oauth_input)
      return {"success": True, "oauth": result}
    else:
      raise ValueError(f"Unknown OAuth action: {oauth_action}")
  except Exception as e:
    import traceback
    return {
      "success": False,
      "error": {
        "code": "oauth_error",
        "message": str(e) + "\n" + traceback.format_exc()
      }
    }

async def handle_callbacks_action(event: Dict[str, Any]) -> Dict[str, Any]:
  try:
    load_user_server({})
    
    callback_action = event.get('callbackAction')
    callback_input = event.get('callbackInput', {})
    
    if callback_action == 'get':
      result = await callbacks.handle_callbacks_get()
      return {"success": True, "callbacks": result}
    elif callback_action == 'handle':
      result = await callbacks.handle_callbacks_handle(callback_input)
      return {"success": True, "callbacks": result}
    elif callback_action == 'install':
      result = await callbacks.handle_callbacks_install(callback_input)
      return {"success": True, "callbacks": result}
    elif callback_action == 'poll':
      result = await callbacks.handle_callbacks_poll(callback_input)
      return {"success": True, "callbacks": result}
    else:
      raise ValueError(f"Unknown callback action: {callback_action}")
  except Exception as e:
    import traceback
    return {
      "success": False,
      "error": {
        "code": "callback_error",
        "message": str(e) + "\n" + traceback.format_exc()
      }
    }

