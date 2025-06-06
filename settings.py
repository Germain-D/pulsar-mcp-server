from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuration settings for Pulsar MCP Server."""
    
    # Pulsar connection settings
    pulsar_service_url: str = "pulsar://localhost:6650"
    pulsar_web_service_url: str = "http://localhost:8080"
    
    # Topic and subscription settings
    topic_name: str = "my-topic"
    subscription_name: str = "pulsar-mcp-subscription"
    subscription_type: str = "Shared"
    is_topic_read_from_beginning: bool = False
    
    # Authentication settings (optional)
    pulsar_token: Optional[str] = None
    pulsar_tls_trust_certs_file_path: Optional[str] = None
    pulsar_tls_allow_insecure_connection: bool = False
    
    # Tool descriptions (optional)
    tool_publish_description: str = "Publishes information to the configured Pulsar topic"
    tool_consume_description: str = "Consumes information from the configured Pulsar topic"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings() 