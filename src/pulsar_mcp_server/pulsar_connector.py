import asyncio
import logging
import pulsar
from pulsar import ConsumerType, InitialPosition
from typing import Optional, List, Dict, Any
from .settings import settings

logger = logging.getLogger(__name__)


class PulsarConnector:
    """Pulsar connector for MCP server operations."""
    
    def __init__(self):
        self.client: Optional[pulsar.Client] = None
        self.producer: Optional[pulsar.Producer] = None
        self.consumer: Optional[pulsar.Consumer] = None
        self._is_connected = False
    
    async def connect(self) -> bool:
        """Connect to Pulsar cluster."""
        try:
            # Build client configuration
            client_config = {
                'service_url': settings.pulsar_service_url,
            }
            
            # Add authentication if provided
            if settings.pulsar_token:
                client_config['authentication'] = pulsar.AuthenticationToken(settings.pulsar_token)
            
            # Add TLS configuration if provided
            if settings.pulsar_tls_trust_certs_file_path:
                client_config['tls_trust_certs_file_path'] = settings.pulsar_tls_trust_certs_file_path
                client_config['tls_allow_insecure_connection'] = settings.pulsar_tls_allow_insecure_connection
            
            self.client = pulsar.Client(**client_config)
            self._is_connected = True
            logger.info(f"Connected to Pulsar at {settings.pulsar_service_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Pulsar: {e}")
            self._is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Pulsar cluster."""
        try:
            if self.consumer:
                self.consumer.close()
                self.consumer = None
            
            if self.producer:
                self.producer.close()
                self.producer = None
            
            if self.client:
                self.client.close()
                self.client = None
            
            self._is_connected = False
            logger.info("Disconnected from Pulsar")
            
        except Exception as e:
            logger.error(f"Error during disconnection: {e}")
    
    async def publish_message(self, topic: str, message: str, properties: Optional[Dict[str, str]] = None) -> bool:
        """Publish a message to a Pulsar topic."""
        try:
            if not self._is_connected:
                await self.connect()
            
            if not self.producer or self.producer.topic() != topic:
                if self.producer:
                    self.producer.close()
                
                self.producer = self.client.create_producer(
                    topic,
                    send_timeout_millis=30000,
                    batching_enabled=True
                )
            
            # Send message
            message_id = self.producer.send(
                message.encode('utf-8'),
                properties=properties or {}
            )
            
            logger.info(f"Message published to topic {topic} with ID: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message to topic {topic}: {e}")
            return False
    
    async def consume_messages(self, topic: str, subscription_name: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Consume messages from a Pulsar topic."""
        try:
            if not self._is_connected:
                await self.connect()
            
            # Create consumer if not exists or topic changed
            if not self.consumer or self.consumer.topic() != topic:
                if self.consumer:
                    self.consumer.close()
                
                # Determine consumer type
                consumer_type_map = {
                    "Exclusive": ConsumerType.Exclusive,
                    "Shared": ConsumerType.Shared,
                    "Failover": ConsumerType.Failover,
                    "KeyShared": ConsumerType.KeyShared
                }
                
                consumer_type = consumer_type_map.get(
                    settings.subscription_type, 
                    ConsumerType.Shared
                )
                
                # Determine initial position
                initial_position = (
                    InitialPosition.Earliest 
                    if settings.is_topic_read_from_beginning 
                    else InitialPosition.Latest
                )
                
                self.consumer = self.client.subscribe(
                    topic,
                    subscription_name,
                    consumer_type=consumer_type,
                    initial_position=initial_position
                )
            
            messages = []
            for _ in range(max_messages):
                try:
                    # Receive message with timeout
                    msg = self.consumer.receive(timeout_millis=1000)
                    
                    message_data = {
                        'message_id': str(msg.message_id()),
                        'data': msg.data().decode('utf-8'),
                        'properties': msg.properties(),
                        'topic': msg.topic_name(),
                        'publish_timestamp': msg.publish_timestamp(),
                        'event_timestamp': msg.event_timestamp()
                    }
                    
                    messages.append(message_data)
                    
                    # Acknowledge message
                    self.consumer.acknowledge(msg)
                    
                except pulsar.Timeout:
                    # No more messages available
                    break
            
            logger.info(f"Consumed {len(messages)} messages from topic {topic}")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to consume messages from topic {topic}: {e}")
            return []
    
    async def create_topic(self, topic: str, partitions: int = 1) -> bool:
        """Create a new topic."""
        try:
            if not self._is_connected:
                await self.connect()
            
            # Use admin API to create topic
            import requests
            
            url = f"{settings.pulsar_web_service_url}/admin/v2/persistent/public/default/{topic}/partitions"
            
            headers = {}
            if settings.pulsar_token:
                headers['Authorization'] = f'Bearer {settings.pulsar_token}'
            
            response = requests.put(url, json=partitions, headers=headers)
            
            if response.status_code in [204, 409]:  # 204: created, 409: already exists
                logger.info(f"Topic {topic} created/exists with {partitions} partitions")
                return True
            else:
                logger.error(f"Failed to create topic {topic}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create topic {topic}: {e}")
            return False
    
    async def delete_topic(self, topic: str) -> bool:
        """Delete a topic."""
        try:
            import requests
            
            url = f"{settings.pulsar_web_service_url}/admin/v2/persistent/public/default/{topic}"
            
            headers = {}
            if settings.pulsar_token:
                headers['Authorization'] = f'Bearer {settings.pulsar_token}'
            
            response = requests.delete(url, headers=headers)
            
            if response.status_code in [204, 404]:  # 204: deleted, 404: not found
                logger.info(f"Topic {topic} deleted or not found")
                return True
            else:
                logger.error(f"Failed to delete topic {topic}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete topic {topic}: {e}")
            return False
    
    async def list_topics(self) -> List[str]:
        """List all topics."""
        try:
            import requests
            
            url = f"{settings.pulsar_web_service_url}/admin/v2/persistent/public/default"
            
            headers = {}
            if settings.pulsar_token:
                headers['Authorization'] = f'Bearer {settings.pulsar_token}'
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                topics = response.json()
                logger.info(f"Found {len(topics)} topics")
                return topics
            else:
                logger.error(f"Failed to list topics: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to list topics: {e}")
            return []
    
    async def get_topic_stats(self, topic: str) -> Dict[str, Any]:
        """Get topic statistics."""
        try:
            import requests
            
            url = f"{settings.pulsar_web_service_url}/admin/v2/persistent/public/default/{topic}/stats"
            
            headers = {}
            if settings.pulsar_token:
                headers['Authorization'] = f'Bearer {settings.pulsar_token}'
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                stats = response.json()
                logger.info(f"Retrieved stats for topic {topic}")
                return stats
            else:
                logger.error(f"Failed to get topic stats for {topic}: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get topic stats for {topic}: {e}")
            return {}

    async def list_connectors(self, connector_type: str = "source") -> List[str]:
        """List all connectors of specified type (source or sink)."""
        try:
            import requests
            
            if connector_type not in ["source", "sink"]:
                logger.error(f"Invalid connector type: {connector_type}. Must be 'source' or 'sink'")
                return []
            
            url = f"{settings.pulsar_web_service_url}/admin/v3/functions/public/default"
            
            headers = {}
            if settings.pulsar_token:
                headers['Authorization'] = f'Bearer {settings.pulsar_token}'
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                all_functions = response.json()
                # Filter for connectors by checking if they have connector-specific properties
                connectors = []
                
                for func_name in all_functions:
                    func_info = await self.get_connector_config(func_name)
                    if func_info and self._is_connector(func_info, connector_type):
                        connectors.append(func_name)
                
                logger.info(f"Found {len(connectors)} {connector_type} connectors")
                return connectors
            else:
                logger.error(f"Failed to list connectors: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to list connectors: {e}")
            return []

    async def get_connector_status(self, connector_name: str) -> Dict[str, Any]:
        """Get the status of a specific connector."""
        try:
            import requests
            
            # Try to get status as a function first (Pulsar IO connectors are functions)
            url = f"{settings.pulsar_web_service_url}/admin/v3/functions/public/default/{connector_name}/status"
            
            headers = {}
            if settings.pulsar_token:
                headers['Authorization'] = f'Bearer {settings.pulsar_token}'
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                status = response.json()
                logger.info(f"Retrieved status for connector {connector_name}")
                return {
                    "connector_name": connector_name,
                    "status": status,
                    "type": "function"
                }
            else:
                # Try source connector specific endpoint
                source_url = f"{settings.pulsar_web_service_url}/admin/v3/sources/public/default/{connector_name}/status"
                source_response = requests.get(source_url, headers=headers)
                
                if source_response.status_code == 200:
                    status = source_response.json()
                    logger.info(f"Retrieved source connector status for {connector_name}")
                    return {
                        "connector_name": connector_name,
                        "status": status,
                        "type": "source"
                    }
                
                # Try sink connector specific endpoint
                sink_url = f"{settings.pulsar_web_service_url}/admin/v3/sinks/public/default/{connector_name}/status"
                sink_response = requests.get(sink_url, headers=headers)
                
                if sink_response.status_code == 200:
                    status = sink_response.json()
                    logger.info(f"Retrieved sink connector status for {connector_name}")
                    return {
                        "connector_name": connector_name,
                        "status": status,
                        "type": "sink"
                    }
                
                logger.error(f"Failed to get connector status for {connector_name}: Function={response.text}, Source={source_response.text}, Sink={sink_response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get connector status for {connector_name}: {e}")
            return {}

    async def get_connector_config(self, connector_name: str) -> Dict[str, Any]:
        """Get the configuration of a specific connector."""
        try:
            import requests
            
            # Try to get config as a function first
            url = f"{settings.pulsar_web_service_url}/admin/v3/functions/public/default/{connector_name}"
            
            headers = {}
            if settings.pulsar_token:
                headers['Authorization'] = f'Bearer {settings.pulsar_token}'
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                config = response.json()
                logger.info(f"Retrieved config for connector {connector_name}")
                return {
                    "connector_name": connector_name,
                    "config": config,
                    "type": "function"
                }
            else:
                # Try source connector specific endpoint
                source_url = f"{settings.pulsar_web_service_url}/admin/v3/sources/public/default/{connector_name}"
                source_response = requests.get(source_url, headers=headers)
                
                if source_response.status_code == 200:
                    config = source_response.json()
                    logger.info(f"Retrieved source connector config for {connector_name}")
                    return {
                        "connector_name": connector_name,
                        "config": config,
                        "type": "source"
                    }
                
                # Try sink connector specific endpoint
                sink_url = f"{settings.pulsar_web_service_url}/admin/v3/sinks/public/default/{connector_name}"
                sink_response = requests.get(sink_url, headers=headers)
                
                if sink_response.status_code == 200:
                    config = sink_response.json()
                    logger.info(f"Retrieved sink connector config for {connector_name}")
                    return {
                        "connector_name": connector_name,
                        "config": config,
                        "type": "sink"
                    }
                
                logger.error(f"Failed to get connector config for {connector_name}: Function={response.text}, Source={source_response.text}, Sink={sink_response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get connector config for {connector_name}: {e}")
            return {}

    def _is_connector(self, func_info: Dict[str, Any], connector_type: str) -> bool:
        """Helper method to determine if a function is a connector of the specified type."""
        if not func_info or "config" not in func_info:
            return False
        
        config = func_info["config"]
        
        # Check for source connector indicators
        if connector_type == "source":
            return any([
                "sourceDetails" in config,
                "source" in config,
                "source" in config.get("className", "").lower(),
                "source" in config.get("archive", "").lower()
            ])
        
        # Check for sink connector indicators  
        elif connector_type == "sink":
            return any([
                "sinkDetails" in config,
                "sink" in config,
                "sink" in config.get("className", "").lower(),
                "sink" in config.get("archive", "").lower()
            ])
        
        return False

    async def get_all_connectors(self) -> Dict[str, List[str]]:
        """Get all connectors organized by type."""
        try:
            source_connectors = await self.list_connectors("source")
            sink_connectors = await self.list_connectors("sink")
            
            return {
                "source": source_connectors,
                "sink": sink_connectors,
                "total_source": len(source_connectors),
                "total_sink": len(sink_connectors),
                "total": len(source_connectors) + len(sink_connectors)
            }
        except Exception as e:
            logger.error(f"Failed to get all connectors: {e}")
            return {
                "source": [],
                "sink": [],
                "total_source": 0,
                "total_sink": 0,
                "total": 0
            }

 