"""In-process transport for MCP client-server communication."""
import anyio
from typing import Tuple
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp.shared.message import SessionMessage


def create_in_process_transport() -> Tuple[
    Tuple[MemoryObjectSendStream, MemoryObjectReceiveStream],
    Tuple[MemoryObjectSendStream, MemoryObjectReceiveStream]
]:
    """
    Create bidirectional in-process transport for client-server communication.
    
    Returns:
        ((server_send, server_receive), (client_send, client_receive))
    """
    server_to_client_send, server_to_client_receive = anyio.create_memory_object_stream[SessionMessage](0)
    client_to_server_send, client_to_server_receive = anyio.create_memory_object_stream[SessionMessage](0)
    
    server_streams = (server_to_client_send, client_to_server_receive)
    
    client_streams = (client_to_server_send, server_to_client_receive)
    
    return server_streams, client_streams

