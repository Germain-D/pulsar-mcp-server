import asyncio

from .server import run_stdio
from .settings import ServerSettings
from .pulsar_connector import PulsarConnector


def main():
    """Run the server sourcing configuration from environment variables."""
    asyncio.run(run_stdio(ServerSettings(), PulsarConnector()))


# Optionally expose other important items at package level
__all__ = ["main", "run_stdio", "ServerSettings", "PulsarConnector"] 