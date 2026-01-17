"""
Tavily MCP Integration - Complete Version
"""

import asyncio
import os
from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()


class GymandoTavilySearch:
    """Search the web using Tavily MCP"""
    
    def __init__(self):
        """Initialize the search class"""
        self.client = Anthropic()
        print("✅ GymandoTavilySearch initialized!")
    
    async def search_with_mcp(self, query: str):
        """Search using Tavily MCP server"""
        
        # Check for Tavily API key
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable is required")
        
        # Configure MCP server parameters with environment variables
        env = {
            **os.environ,  # Inherit existing environment
            "TAVILY_API_KEY": tavily_api_key,  # Set Tavily API key
            "NODE_ENV": "production",  # Suppress development logs
            "LOG_LEVEL": "silent",  # Suppress logging output
            "SILENT": "1",  # Alternative silent flag
        }
        
        server_params = StdioServerParameters(
            command="npx",
            args=["--quiet", "-y", "tavily-mcp@latest"],  # --quiet suppresses npx output, -y auto-installs
            env=env
        )
        
        print(f"🔍 Searching for: '{query}'")
        print("📡 Starting Tavily MCP server...")
        
        # Connect to MCP server
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize session
                await session.initialize()
                print("✅ Tavily MCP server connected!\n")
                
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
                
                # Ask Claude to search
                messages = [{"role": "user", "content": query}]
                
                print("🤖 Asking Claude to search...\n")
                
                # Initial request to Claude
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system="You should only answer queries related to exercises, workouts, and fitness. Do not answer any query not related to exercises.",
                    messages=messages,
                    tools=anthropic_tools
                )
                
                # Handle tool use - Tavily might make multiple tool calls
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
                        print("⏳ Fetching search results...\n")
                        tool_result = await session.call_tool(tool_name, tool_input)
                        
                        print("✅ Search results received!\n")
                        
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
                        system="You should only answer queries related to exercises, workouts, and fitness. Do not answer any query not related to exercises.",
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
    
    def search(self, query: str):
        """Synchronous wrapper for search_with_mcp"""
        return asyncio.run(self.search_with_mcp(query))


# Test it
if __name__ == "__main__":
    searcher = GymandoTavilySearch()
    while True:
        user_input = input("Give your question: ")
        if user_input == "q":
            break
        result = searcher.search(user_input)
