"""Client management for MCP sessions - Python equivalent of server.ts."""
import asyncio
import sys
from typing import Any, Dict, Optional
from mcp.client.session import ClientSession
from mcp.server.session import ServerSession
from mcp.types import Implementation

from .transport import create_in_process_transport

_clients: Dict[str, ClientSession] = {}
_client_tasks: Dict[str, asyncio.Task] = {}


async def get_client(args: Dict[str, Any], participant_json: Dict[str, Any]) -> ClientSession:
    """
    Get or create an MCP client connected to the user's server.
    
    Maintains a cache of clients by name to avoid recreating connections.
    """
    client_name = participant_json.get('clientInfo', {}).get('name', 'Metorial')
    
    if client_name in _clients:
        return _clients[client_name]
    
    import builtins
    from . import config
    
    config.set_args(args)
    
    server = getattr(builtins, '__metorial_server__', None)
    if server is None:
        raise RuntimeError("No MCP server found. Did you call metorial.create_server()?")
    
    server_streams, client_streams = create_in_process_transport()
    
    server_session = ServerSession(
        server_streams[1],  # read stream
        server_streams[0]   # write stream
    )
    
    client_session = ClientSession(
        client_streams[1],  # read stream
        client_streams[0],  # write stream
        client_info=Implementation(
            name=participant_json.get('clientInfo', {}).get('name', 'Metorial'),
            version=participant_json.get('clientInfo', {}).get('version', '1.0.0')
        )
    )
    
    async def run_server_session():
        """Keep the server session running."""
        try:
            await server._handle_session(server_session)
        except Exception as e:
            print(f"ERROR: Server session failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    task = asyncio.create_task(run_server_session())
    _client_tasks[client_name] = task
    
    await asyncio.sleep(0.01)
    
    await client_session.initialize()
    
    _clients[client_name] = client_session
    
    return client_session

