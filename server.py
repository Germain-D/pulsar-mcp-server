import asyncio
import logging
from typing import Any, Dict, List, Optional
from mcp import Tool
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    CallToolResult,
    TextContent,
)

from pulsar_connector import PulsarConnector
from settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Pulsar connector
pulsar_connector = PulsarConnector()

# Create MCP server
server = Server("pulsar-mcp-server")


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools for Pulsar operations."""
    return [
        Tool(
            name="pulsar-publish",
            description=settings.tool_publish_description,
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string", 
                        "description": "The Pulsar topic to publish to"
                    },
                    "message": {
                        "type": "string", 
                        "description": "The message content to publish"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Optional message properties as key-value pairs",
                        "additionalProperties": {"type": "string"}
                    }
                },
                "required": ["topic", "message"]
            }
        ),
        Tool(
            name="pulsar-consume",
            description=settings.tool_consume_description,
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The Pulsar topic to consume from"
                    },
                    "subscription_name": {
                        "type": "string",
                        "description": "The subscription name for consuming messages",
                        "default": settings.subscription_name
                    },
                    "max_messages": {
                        "type": "integer",
                        "description": "Maximum number of messages to consume",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="pulsar-create-topic",
            description="Creates a new Pulsar topic with specified parameters",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Name of the topic to create"
                    },
                    "partitions": {
                        "type": "integer",
                        "description": "Number of partitions to allocate",
                        "default": 1,
                        "minimum": 1
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="pulsar-delete-topic",
            description="Deletes an existing Pulsar topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Name of the topic to delete"
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="pulsar-list-topics",
            description="Lists all topics in the Pulsar cluster",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="pulsar-topic-stats",
            description="Retrieves statistics and metadata about a topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Name of the topic to get stats for"
                    }
                },
                "required": ["topic"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Optional[Dict[str, Any]]
) -> CallToolResult:
    """Handle tool calls for Pulsar operations."""
    try:
        if name == "pulsar-publish":
            return await handle_publish_tool(arguments or {})
        elif name == "pulsar-consume":
            return await handle_consume_tool(arguments or {})
        elif name == "pulsar-create-topic":
            return await handle_create_topic_tool(arguments or {})
        elif name == "pulsar-delete-topic":
            return await handle_delete_topic_tool(arguments or {})
        elif name == "pulsar-list-topics":
            return await handle_list_topics_tool(arguments or {})
        elif name == "pulsar-topic-stats":
            return await handle_topic_stats_tool(arguments or {})
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")]
        )


async def handle_publish_tool(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle pulsar-publish tool."""
    topic = arguments.get("topic", settings.topic_name)
    message = arguments.get("message")
    properties = arguments.get("properties", {})
    
    if not message:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: Message content is required")]
        )
    
    success = await pulsar_connector.publish_message(topic, message, properties)
    
    if success:
        result_text = f"Successfully published message to topic '{topic}'"
        if properties:
            result_text += f" with properties: {properties}"
    else:
        result_text = f"Failed to publish message to topic '{topic}'"
    
    return CallToolResult(
        content=[TextContent(type="text", text=result_text)]
    )


async def handle_consume_tool(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle pulsar-consume tool."""
    topic = arguments.get("topic", settings.topic_name)
    subscription_name = arguments.get("subscription_name", settings.subscription_name)
    max_messages = arguments.get("max_messages", 10)
    
    messages = await pulsar_connector.consume_messages(topic, subscription_name, max_messages)
    
    if messages:
        result_text = f"Consumed {len(messages)} messages from topic '{topic}':\n\n"
        for i, msg in enumerate(messages, 1):
            result_text += f"Message {i}:\n"
            result_text += f"  ID: {msg['message_id']}\n"
            result_text += f"  Data: {msg['data']}\n"
            if msg['properties']:
                result_text += f"  Properties: {msg['properties']}\n"
            result_text += f"  Publish Time: {msg['publish_timestamp']}\n"
            result_text += "\n"
    else:
        result_text = f"No messages found in topic '{topic}'"
    
    return CallToolResult(
        content=[TextContent(type="text", text=result_text)]
    )


async def handle_create_topic_tool(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle pulsar-create-topic tool."""
    topic = arguments.get("topic")
    partitions = arguments.get("partitions", 1)
    
    if not topic:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: Topic name is required")]
        )
    
    success = await pulsar_connector.create_topic(topic, partitions)
    
    if success:
        result_text = f"Successfully created topic '{topic}' with {partitions} partitions"
    else:
        result_text = f"Failed to create topic '{topic}'"
    
    return CallToolResult(
        content=[TextContent(type="text", text=result_text)]
    )


async def handle_delete_topic_tool(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle pulsar-delete-topic tool."""
    topic = arguments.get("topic")
    
    if not topic:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: Topic name is required")]
        )
    
    success = await pulsar_connector.delete_topic(topic)
    
    if success:
        result_text = f"Successfully deleted topic '{topic}'"
    else:
        result_text = f"Failed to delete topic '{topic}'"
    
    return CallToolResult(
        content=[TextContent(type="text", text=result_text)]
    )


async def handle_list_topics_tool(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle pulsar-list-topics tool."""
    topics = await pulsar_connector.list_topics()
    
    if topics:
        result_text = f"Found {len(topics)} topics:\n\n"
        for topic in topics:
            result_text += f"  - {topic}\n"
    else:
        result_text = "No topics found or error retrieving topics"
    
    return CallToolResult(
        content=[TextContent(type="text", text=result_text)]
    )


async def handle_topic_stats_tool(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle pulsar-topic-stats tool."""
    topic = arguments.get("topic")
    
    if not topic:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: Topic name is required")]
        )
    
    stats = await pulsar_connector.get_topic_stats(topic)
    
    if stats:
        result_text = f"Statistics for topic '{topic}':\n\n"
        
        # Format key statistics
        if "msgRateIn" in stats:
            result_text += f"Message Rate In: {stats['msgRateIn']:.2f} msg/s\n"
        if "msgRateOut" in stats:
            result_text += f"Message Rate Out: {stats['msgRateOut']:.2f} msg/s\n"
        if "msgThroughputIn" in stats:
            result_text += f"Throughput In: {stats['msgThroughputIn']:.2f} bytes/s\n"
        if "msgThroughputOut" in stats:
            result_text += f"Throughput Out: {stats['msgThroughputOut']:.2f} bytes/s\n"
        if "storageSize" in stats:
            result_text += f"Storage Size: {stats['storageSize']} bytes\n"
        if "averageMsgSize" in stats:
            result_text += f"Average Message Size: {stats['averageMsgSize']:.2f} bytes\n"
        
        # Add subscription information
        if "subscriptions" in stats:
            result_text += f"\nSubscriptions ({len(stats['subscriptions'])}):\n"
            for sub_name, sub_stats in stats["subscriptions"].items():
                result_text += f"  - {sub_name}:\n"
                if "msgBacklog" in sub_stats:
                    result_text += f"    Backlog: {sub_stats['msgBacklog']} messages\n"
                if "msgRateOut" in sub_stats:
                    result_text += f"    Rate Out: {sub_stats['msgRateOut']:.2f} msg/s\n"
    else:
        result_text = f"Failed to retrieve statistics for topic '{topic}'"
    
    return CallToolResult(
        content=[TextContent(type="text", text=result_text)]
    )


async def cleanup():
    """Cleanup resources on server shutdown."""
    await pulsar_connector.disconnect()


# Add cleanup handler
server.close_handler = cleanup 