"""Bootstrap module for Metorial Python Lambda handlers - REWRITTEN."""
import asyncio
import json
import sys
import os
import importlib.util
import builtins
from typing import Any, Dict, Optional
from io import StringIO

import anyio
from mcp.client.session import ClientSession
from mcp.server.session import ServerSession
from mcp.types import Implementation, McpError

from . import config
from . import oauth
from . import callbacks
from .transport import create_in_process_transport

_user_module_loaded = False
_server = None
_handlers = {}
_clients = {}

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
    
    # Collect stdout
    if self.stdout_capture:
      stdout_text = self.stdout_capture.getvalue()
      if stdout_text.strip():
        self.logs.append({
          "type": "info",
          "lines": stdout_text.strip().split('\n')
        })
    
    # Collect stderr
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

async def get_client(args: Dict[str, Any], participant_json: Dict[str, Any]) -> ClientSession:
  """Get or create an MCP client connected to the user's server."""
  client_name = participant_json.get('clientInfo', {}).get('name', 'default')
  
  if client_name in _clients:
    return _clients[client_name]
  
  # Load the user's server
  server, _ = load_user_server(args)
  
  # Create in-process transport
  server_streams, client_streams = create_in_process_transport()
  
  # Create server session
  server_session = ServerSession(
    server_streams[1],  # read from client
    server_streams[0]   # write to client
  )
  
  # Create client session
  client_session = ClientSession(
    client_streams[1],  # read from server
    client_streams[0],  # write to server
    client_info=Implementation(
      name=participant_json.get('clientInfo', {}).get('name', 'Metorial'),
      version=participant_json.get('clientInfo', {}).get('version', '1.0.0')
    )
  )
  
  # Start both sessions in background task group
  async def run_sessions():
    async with anyio.create_task_group() as tg:
      # Run server session
      tg.start_soon(server._handle_session, server_session)
      # Keep running
      await anyio.sleep_forever()
  
  # Start background task
  asyncio.create_task(run_sessions())
  
  # Initialize client (does the handshake including initialize)
  await client_session.initialize()
  
  _clients[client_name] = client_session
  return client_session

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
    
    return {
      "success": True,
      "discovery": {
        "tools": tools,
        "resourceTemplates": resource_templates,
        "prompts": prompts,
        "capabilities": {},
        "implementation": {
          "name": server.name if hasattr(server, 'name') else "unknown",
          "version": "1.0.0"
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
  """
  Handle MCP requests by forwarding them through a client session.
  This matches the JavaScript implementation which uses the MCP SDK Client.
  """
  try:
    # Parse args and participant info
    args_raw = event.get('args', '{}')
    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
    
    participant_raw = event.get('participantJson', '{}')
    participant_json = json.loads(participant_raw) if isinstance(participant_raw, str) else participant_raw
    
    # Get connected client (this handles initialize automatically)
    client = await get_client(args, participant_json)
    
    messages_raw = event.get('messages', [])
    
    responses = []
    notifications = []
    
    # Process each message
    for message_raw in messages_raw:
      message = json.loads(message_raw) if isinstance(message_raw, str) else message_raw
      
      try:
        # If message has 'id', it's a request; otherwise it's a notification
        if 'id' in message:
          # Forward request to client - SDK handles all protocol methods automatically
          result = await client.send_request(
            message.get('method'),
            message.get('params', {})
          )
          
          responses.append({
            "jsonrpc": "2.0",
            "id": message['id'],
            "result": result
          })
        else:
          # It's a notification (no response needed)
          await client.send_notification(
            message.get('method'),
            message.get('params', {})
          )
          # Notifications might generate server notifications
          notifications.append(message)
      
      except McpError as e:
        responses.append({
          "jsonrpc": "2.0",
          "id": message.get('id'),
          "error": {
            "code": e.code,
            "message": e.message,
            "data": e.data if hasattr(e, 'data') else None
          }
        })
      except Exception as e:
        responses.append({
          "jsonrpc": "2.0",
          "id": message.get('id'),
          "error": {
            "code": -32603,
            "message": str(e)
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

