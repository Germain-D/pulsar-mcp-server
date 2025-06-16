import json
from collections.abc import Sequence
from typing import Any
import traceback

import mcp.types as types
from mcp.server import Server
from pydantic import ValidationError

from .pulsar_connector import PulsarConnector
from .settings import ServerSettings

app = Server("pulsar-server")
_pulsar_connector: PulsarConnector
_server_settings: ServerSettings


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools for Pulsar operations."""
    return [
        types.Tool(
            name="pulsar_publish",
            description="Publish a message to a Pulsar topic",
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
        types.Tool(
            name="pulsar_consume",
            description="Consume messages from a Pulsar topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The Pulsar topic to consume from"
                    },
                    "subscription_name": {
                        "type": "string",
                        "description": "The subscription name for consuming messages"
                    },
                    "max_messages": {
                        "type": "integer",
                        "description": "Maximum number of messages to consume",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["topic", "subscription_name"]
            }
        ),
        types.Tool(
            name="pulsar_create_topic",
            description="Create a new Pulsar topic",
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
        types.Tool(
            name="pulsar_delete_topic",
            description="Delete an existing Pulsar topic",
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
        types.Tool(
            name="pulsar_list_topics",
            description="List all topics in the Pulsar cluster",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="pulsar_topic_stats",
            description="Get statistics and metadata about a topic",
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
        ),
        types.Tool(
            name="pulsar_list_connectors",
            description="List all connectors of specified type (source or sink)",
            inputSchema={
                "type": "object",
                "properties": {
                    "connector_type": {
                        "type": "string",
                        "description": "Type of connectors to list",
                        "enum": ["source", "sink"],
                        "default": "source"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="pulsar_connector_status",
            description="Get the status of a specific connector",
            inputSchema={
                "type": "object",
                "properties": {
                    "connector_name": {
                        "type": "string",
                        "description": "Name of the connector to get status for"
                    }
                },
                "required": ["connector_name"]
            }
        ),
        types.Tool(
            name="pulsar_connector_config",
            description="Get the configuration of a specific connector",
            inputSchema={
                "type": "object",
                "properties": {
                    "connector_name": {
                        "type": "string",
                        "description": "Name of the connector to get configuration for"
                    }
                },
                "required": ["connector_name"]
            }
        ),
        types.Tool(
            name="pulsar_all_connectors",
            description="Get all connectors organized by type (source and sink)",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
    ]


@app.call_tool()
async def call_tool(
    name: str, arguments: Any
) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if arguments is None:
        arguments = {}

    result = None

    try:
        if name == "pulsar_publish":
            topic = arguments.get("topic", _server_settings.topic_name)
            message = arguments.get("message")
            properties = arguments.get("properties", {})
            
            if not message:
                raise ValueError("Message content is required")
            
            success = await _pulsar_connector.publish_message(topic, message, properties)
            
            if success:
                result_text = f"Successfully published message to topic '{topic}'"
                if properties:
                    result_text += f" with properties: {properties}"
                result = {"status": "success", "message": result_text}
            else:
                result = {"status": "error", "message": f"Failed to publish message to topic '{topic}'"}

        elif name == "pulsar_consume":
            topic = arguments.get("topic", _server_settings.topic_name)
            subscription_name = arguments.get("subscription_name", _server_settings.subscription_name)
            max_messages = arguments.get("max_messages", 10)
            
            messages = await _pulsar_connector.consume_messages(topic, subscription_name, max_messages)
            
            if messages:
                result = {
                    "status": "success",
                    "topic": topic,
                    "subscription": subscription_name,
                    "message_count": len(messages),
                    "messages": messages
                }
            else:
                result = {
                    "status": "success",
                    "topic": topic,
                    "subscription": subscription_name,
                    "message_count": 0,
                    "message": "No messages available"
                }

        elif name == "pulsar_create_topic":
            topic = arguments.get("topic")
            partitions = arguments.get("partitions", 1)
            
            if not topic:
                raise ValueError("Topic name is required")
            
            success = await _pulsar_connector.create_topic(topic, partitions)
            
            if success:
                result = {"status": "success", "message": f"Topic '{topic}' created successfully with {partitions} partitions"}
            else:
                result = {"status": "error", "message": f"Failed to create topic '{topic}'"}

        elif name == "pulsar_delete_topic":
            topic = arguments.get("topic")
            
            if not topic:
                raise ValueError("Topic name is required")
            
            success = await _pulsar_connector.delete_topic(topic)
            
            if success:
                result = {"status": "success", "message": f"Topic '{topic}' deleted successfully"}
            else:
                result = {"status": "error", "message": f"Failed to delete topic '{topic}'"}

        elif name == "pulsar_list_topics":
            topics = await _pulsar_connector.list_topics()
            result = {"status": "success", "topics": topics, "count": len(topics)}

        elif name == "pulsar_topic_stats":
            topic = arguments.get("topic")
            
            if not topic:
                raise ValueError("Topic name is required")
            
            stats = await _pulsar_connector.get_topic_stats(topic)
            
            if stats:
                result = {"status": "success", "topic": topic, "stats": stats}
            else:
                result = {"status": "error", "message": f"Failed to get stats for topic '{topic}'"}

        elif name == "pulsar_list_connectors":
            connector_type = arguments.get("connector_type", "source")
            
            connectors = await _pulsar_connector.list_connectors(connector_type)
            result = {
                "status": "success", 
                "connector_type": connector_type,
                "connectors": connectors, 
                "count": len(connectors)
            }

        elif name == "pulsar_connector_status":
            connector_name = arguments.get("connector_name")
            
            if not connector_name:
                raise ValueError("Connector name is required")
            
            status = await _pulsar_connector.get_connector_status(connector_name)
            
            if status:
                result = {"status": "success", "connector_status": status}
            else:
                result = {"status": "error", "message": f"Failed to get status for connector '{connector_name}'"}

        elif name == "pulsar_connector_config":
            connector_name = arguments.get("connector_name")
            
            if not connector_name:
                raise ValueError("Connector name is required")
            
            config = await _pulsar_connector.get_connector_config(connector_name)
            
            if config:
                result = {"status": "success", "connector_config": config}
            else:
                result = {"status": "error", "message": f"Failed to get config for connector '{connector_name}'"}

        elif name == "pulsar_all_connectors":
            all_connectors = await _pulsar_connector.get_all_connectors()
            result = {"status": "success", "connectors": all_connectors}

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except ValidationError as e:
        await app.request_context.session.send_log_message(
            "error", "Failed to validate input provided by LLM: " + str(e)
        )
        return [
            types.TextContent(
                type="text", text=f"ERROR: You provided invalid Tool inputs: {e}"
            )
        ]

    except Exception as e:
        await app.request_context.session.send_log_message(
            "error", traceback.format_exc()
        )
        raise e

    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]


async def run_stdio(settings: ServerSettings, pulsar_connector: PulsarConnector):
    """Run the server on Standard I/O with the given settings and Pulsar connector."""
    from mcp.server.stdio import stdio_server

    global _pulsar_connector
    _pulsar_connector = pulsar_connector

    global _server_settings
    _server_settings = settings

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options()) 