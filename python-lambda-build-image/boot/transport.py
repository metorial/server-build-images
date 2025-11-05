"""In-process transport for MCP client-server communication using anyio streams."""
from typing import Tuple
import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream


def create_in_process_transport() -> Tuple[
    Tuple[MemoryObjectSendStream, MemoryObjectReceiveStream],
    Tuple[MemoryObjectSendStream, MemoryObjectReceiveStream]
]:
    """
    Create bidirectional in-process transport for client-server communication.
    
    Returns:
        ((server_write, server_read), (client_write, client_read))
    """
    server_to_client_send, server_to_client_receive = anyio.create_memory_object_stream(0)
    client_to_server_send, client_to_server_receive = anyio.create_memory_object_stream(0)
    
    server_streams = (server_to_client_send, client_to_server_receive)
    
    client_streams = (client_to_server_send, server_to_client_receive)
    
    return server_streams, client_streams

