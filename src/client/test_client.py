"""
MCP Client for testing the database server.

This client demonstrates how to connect to an MCP server, list resources/tools/prompts,
and execute operations programmatically.

Usage:
    python src/client/test_client.py
"""

import asyncio
import json
import logging
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPClient:
    """MCP client for interacting with the database server."""
    
    def __init__(self):
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
    
    async def connect(self):
        """Connect to the MCP server via stdio."""
        logger.info("Connecting to MCP server...")
        
        # Server parameters (command to start the server)
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "src.server.mcp_server"],
            env=None
        )
        
        # Establish connection
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )
        
        # Initialize session
        await self.session.initialize()
        logger.info("Connected to MCP server successfully")
    
    async def list_resources(self) -> list:
        """List all available resources."""
        logger.info("Listing resources...")
        response = await self.session.list_resources()
        return response.resources
    
    async def read_resource(self, uri: str) -> str:
        """Read a specific resource."""
        logger.info(f"Reading resource: {uri}")
        response = await self.session.read_resource(uri)
        return response.contents[0].text
    
    async def list_tools(self) -> list:
        """List all available tools."""
        logger.info("Listing tools...")
        response = await self.session.list_tools()
        return response.tools
    
    async def call_tool(self, name: str, arguments: dict) -> str:
        """Call a tool with arguments."""
        logger.info(f"Calling tool: {name} with arguments: {arguments}")
        response = await self.session.call_tool(name, arguments)
        return response.content[0].text
    
    async def list_prompts(self) -> list:
        """List all available prompts."""
        logger.info("Listing prompts...")
        response = await self.session.list_prompts()
        return response.prompts
    
    async def get_prompt(self, name: str, arguments: dict | None = None) -> dict:
        """Get a specific prompt."""
        logger.info(f"Getting prompt: {name}")
        response = await self.session.get_prompt(name, arguments or {})
        return {
            "description": response.description,
            "messages": [
                {"role": msg.role, "content": msg.content.text}
                for msg in response.messages
            ]
        }
    
    async def close(self):
        """Close the connection."""
        await self.exit_stack.aclose()
        logger.info("Connection closed")


async def demo_resources(client: MCPClient):
    """Demonstrate resource operations."""
    print("\n" + "="*60)
    print("DEMO: Resources (Schema & Metadata)")
    print("="*60)
    
    resources = await client.list_resources()
    print(f"\nAvailable resources: {len(resources)}")
    for res in resources:
        print(f"  • {res.name} ({res.uri})")
    
    # Read customer schema
    print("\n--- Customer Schema ---")
    schema = await client.read_resource("db://schema/customers")
    print(json.dumps(json.loads(schema), indent=2))
    
    # Read database stats
    print("\n--- Database Statistics ---")
    stats = await client.read_resource("db://stats/summary")
    print(json.dumps(json.loads(stats), indent=2))


async def demo_tools(client: MCPClient):
    """Demonstrate tool operations."""
    print("\n" + "="*60)
    print("DEMO: Tools (Actions & Queries)")
    print("="*60)
    
    tools = await client.list_tools()
    print(f"\nAvailable tools: {len(tools)}")
    for tool in tools:
        print(f"  • {tool.name}: {tool.description}")
    
    # Query database
    print("\n--- Tool: query_database (Top 5 customers by country) ---")
    result = await client.call_tool(
        "query_database",
        {
            "sql": "SELECT country, COUNT(*) as count FROM customers GROUP BY country ORDER BY count DESC LIMIT 5",
            "limit": 10
        }
    )
    print(json.dumps(json.loads(result), indent=2))
    
    # Get customer orders
    print("\n--- Tool: get_customer_orders (Customer ID=1) ---")
    result = await client.call_tool(
        "get_customer_orders",
        {"customer_id": 1}
    )
    print(json.dumps(json.loads(result), indent=2))
    
    # Analyze product sales
    print("\n--- Tool: analyze_product_sales (Electronics category) ---")
    result = await client.call_tool(
        "analyze_product_sales",
        {"category": "Electronics", "top_n": 5}
    )
    print(json.dumps(json.loads(result), indent=2))


async def demo_prompts(client: MCPClient):
    """Demonstrate prompt templates."""
    print("\n" + "="*60)
    print("DEMO: Prompts (Workflow Templates)")
    print("="*60)
    
    prompts = await client.list_prompts()
    print(f"\nAvailable prompts: {len(prompts)}")
    for prompt in prompts:
        print(f"  • {prompt.name}: {prompt.description}")
        if prompt.arguments:
            print(f"    Arguments: {[arg.name for arg in prompt.arguments]}")
    
    # Get analyze_customer prompt
    print("\n--- Prompt: analyze_customer (Customer ID=1) ---")
    prompt = await client.get_prompt("analyze_customer", {"customer_id": "1"})
    print(f"Description: {prompt['description']}")
    print(f"\nPrompt content:\n{prompt['messages'][0]['content']}")


async def main():
    """Main demo function."""
    print("\n" + "🚀 "*20)
    print("MCP Database Server - Client Demo")
    print("🚀 "*20)
    
    client = MCPClient()
    
    try:
        # Connect to server
        await client.connect()
        
        # Run demos
        await demo_resources(client)
        await demo_tools(client)
        await demo_prompts(client)
        
        print("\n" + "="*60)
        print("✅ All demos completed successfully!")
        print("="*60 + "\n")
    
    except Exception as e:
        logger.error(f"Error during demo: {e}", exc_info=True)
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
