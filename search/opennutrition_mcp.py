"""
OpenNutrition MCP Integration - Complete Version
"""

import asyncio
import os
from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()


class GymandoOpenNutrition:
    """Access nutrition database using OpenNutrition MCP"""
    
    def __init__(self):
        """Initialize the nutrition class"""
        self.client = Anthropic()
        print("✅ GymandoOpenNutrition initialized!")
    
    async def query_with_mcp(self, query: str):
        """Query nutrition database using OpenNutrition MCP server
        
        Note: OpenNutrition MCP is not available via npm. You need to:
        1. Clone the repo: git clone https://github.com/deadletterq/mcp-opennutrition.git
        2. Install: cd mcp-opennutrition && npm install
        3. Build: npm run build
        4. Set OPENNUTRITION_MCP_PATH env var to the built index.js path
           Example: export OPENNUTRITION_MCP_PATH=/path/to/mcp-opennutrition/build/index.js
        """
        
        # Configure MCP server parameters with environment variables
        # OpenNutrition doesn't require an API key - it uses local database
        env = {
            **os.environ,  # Inherit existing environment
            "NODE_ENV": "production",  # Suppress development logs
            "LOG_LEVEL": "silent",  # Suppress logging output
            "SILENT": "1",  # Alternative silent flag
        }
        
        # Check if local path is configured
        local_path = os.getenv("OPENNUTRITION_MCP_PATH")
        if local_path:
            # Use local installation (recommended method)
            if not os.path.exists(local_path):
                raise FileNotFoundError(
                    f"OpenNutrition MCP not found at {local_path}.\n"
                    "Please install it by running:\n"
                    "  1. git clone https://github.com/deadletterq/mcp-opennutrition.git\n"
                    "  2. cd mcp-opennutrition && npm install && npm run build\n"
                    "  3. Set OPENNUTRITION_MCP_PATH=/path/to/mcp-opennutrition/build/index.js"
                )
            server_params = StdioServerParameters(
                command="node",
                args=[os.path.abspath(local_path)],
                env=env
            )
            print(f"📍 Using local OpenNutrition MCP at: {local_path}")
        else:
            # Try using npx with GitHub (may not work - local installation recommended)
            print("⚠️  Warning: OPENNUTRITION_MCP_PATH not set. Attempting to use GitHub via npx...")
            print("   For best results, install locally and set OPENNUTRITION_MCP_PATH")
            server_params = StdioServerParameters(
                command="npx",
                args=["--quiet", "-y", "github:deadletterq/mcp-opennutrition"],
                env=env
            )
        
        print(f"🔍 Querying nutrition database for: '{query}'")
        print("📡 Starting OpenNutrition MCP server...")
        
        # Connect to MCP server
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize session
                await session.initialize()
                print("✅ OpenNutrition MCP server connected!\n")
                
                # List available tools
                tools_response = await session.list_tools()
                print(f"🛠️  Available tools: {[tool.name for tool in tools_response.tools]}\n")
                
                # Convert MCP tools to Anthropic format
                anthropic_tools = []
                for tool in tools_response.tools:
                    anthropic_tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    })
                
                # Ask Claude to query nutrition database
                messages = [{"role": "user", "content": query}]
                
                print("🤖 Asking Claude to query nutrition database...\n")
                
                # Initial request to Claude
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system="You should only answer queries related to nutrition, food, and health. Do not answer any query not related to nutrition.",
                    messages=messages,
                    tools=anthropic_tools
                )
                
                # Handle tool use - OpenNutrition might make multiple tool calls
                while response.stop_reason == "tool_use":
                    # Find tool use blocks (there might be multiple)
                    tool_use_blocks = [
                        block for block in response.content 
                        if block.type == "tool_use"
                    ]
                    
                    # Add assistant response to messages
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    
                    # Process each tool use
                    for tool_use_block in tool_use_blocks:
                        tool_name = tool_use_block.name
                        tool_input = tool_use_block.input
                        
                        print(f"🔧 Claude is using tool: {tool_name}")
                        print(f"   Input: {tool_input}\n")
                        
                        # Call the MCP tool
                        print("⏳ Fetching nutrition data...\n")
                        tool_result = await session.call_tool(tool_name, tool_input)
                        
                        print("✅ Nutrition data received!\n")
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_use_block.id,
                                "content": tool_result.content
                            }]
                        })
                    
                    # Get Claude's next response (might use more tools or provide final answer)
                    response = self.client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=4096,
                        system="You should only answer queries related to nutrition, food, and health. Do not answer any query not related to nutrition.",
                        messages=messages,
                        tools=anthropic_tools
                    )
                
                # Extract final text response
                for block in response.content:
                    if hasattr(block, "text") and block.text:
                        final_text = block.text
                        break
                else:
                    final_text = "No text response found"
                
                print("="*60)
                print("CLAUDE'S ANSWER:")
                print("="*60)
                print(final_text)
                print("="*60)
                
                return final_text
    
    def query(self, query: str):
        """Synchronous wrapper for query_with_mcp"""
        return asyncio.run(self.query_with_mcp(query))


# Test it
if __name__ == "__main__":
    nutrition = GymandoOpenNutrition()
    while True:
        user_input = input("Ask about nutrition: ")
        if user_input == "q":
            break
        result = nutrition.query(user_input)
