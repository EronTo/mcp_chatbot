import argparse
import asyncio
import os
import sys
from typing import Any, Dict, List

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT)

from mcp_chatbot import ChatSession, Configuration, MCPClient
from mcp_chatbot.llm import LLMProvider, create_llm_client


def parse_servers_config(config: Dict[str, Any]) -> List[MCPClient]:
    return [
        MCPClient(name, srv_config) for name, srv_config in config["mcpServers"].items()
    ]


async def main(llm_provider: LLMProvider = "openai") -> None:
    config = Configuration()
    
    server_config = config.load_config("mcp_servers/servers_config.json")
    servers = parse_servers_config(server_config)
    
    llm_client = create_llm_client(llm_provider, config)
    
    chat_session = ChatSession(servers, llm_client)

    try:
        await chat_session.initialize()
        
        # Use R2R search request prompt
        prompt = """
        Search and organize documents related to returns
        """
        
        print("\nSending query:", prompt)
        response = await chat_session.send_message(prompt, show_workflow=True)
        
        print("\nResponse:\n", response)
    finally:
        await chat_session.cleanup_clients()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--llm",
        type=str,
        choices=["openai", "ollama"],
        default="openai",
        help="LLM provider to use (openai or ollama)",
    )
    args = parser.parse_args()

    asyncio.run(main(llm_provider=args.llm))