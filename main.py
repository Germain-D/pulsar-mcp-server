#!/usr/bin/env python3
"""
Pulsar MCP Server - A Message Context Protocol server for Apache Pulsar

This server provides tools to interact with Apache Pulsar through MCP:
- Publish messages to topics
- Consume messages from topics
- Create and delete topics
- List topics and get topic statistics
"""

import argparse
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport

from server import server
from settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def run_server():
    """Context manager for running the MCP server."""
    logger.info("Starting Pulsar MCP Server...")
    logger.info(f"Pulsar Service URL: {settings.pulsar_service_url}")
    logger.info(f"Default Topic: {settings.topic_name}")
    logger.info(f"Subscription Name: {settings.subscription_name}")
    
    try:
        yield server
    finally:
        logger.info("Shutting down Pulsar MCP Server...")
        if hasattr(server, 'close_handler') and server.close_handler:
            await server.close_handler()


async def main():
    """Main entry point for the Pulsar MCP Server."""
    parser = argparse.ArgumentParser(
        description="Pulsar MCP Server - Message Context Protocol server for Apache Pulsar"
    )
    parser.add_argument(
        "--transport", 
        choices=["stdio", "sse"], 
        default="stdio",
        help="Transport method to use (default: stdio)"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to for SSE transport (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3001,
        help="Port to bind to for SSE transport (default: 3001)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        if args.transport == "stdio":
            # Run with stdio transport
            async with run_server() as server_instance:
                async with stdio_server() as (read_stream, write_stream):
                    await server_instance.run(
                        read_stream,
                        write_stream,
                        {}  # Empty initialization options
                    )
        
        elif args.transport == "sse":
            # Run with Server-Sent Events transport
            async with run_server() as server_instance:
                transport = SseServerTransport(f"/messages")
                
                logger.info(f"Starting SSE server on {args.host}:{args.port}")
                logger.info(f"Connect to: http://{args.host}:{args.port}/sse")
                
                await transport.run(
                    host=args.host,
                    port=args.port,
                    server=server_instance
                )
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Handle event loop for different Python versions
    try:
        # Python 3.7+
        asyncio.run(main())
    except AttributeError:
        # Python 3.6
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(main())
        finally:
            loop.close() 