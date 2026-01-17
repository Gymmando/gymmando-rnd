"""
Open WebSearch MCP Integration - Complete Version
"""

import asyncio
import os
from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()


class GymandoSearch:
    """Search the web using Open-WebSearch MCP"""
    
    def __init__(self):
        """Initialize the search class"""
        self.client = Anthropic()
        print("✅ GymandoSearch initialized!")
    
    def test_connection(self):
        """Test if Claude API is working"""
        print("🧪 Testing Claude connection...")
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Say 'Claude is working!' if you can read this."}
            ]
        )
        
        result = response.content[0].text
        print(f"✅ Claude response: {result}\n")
        return result
    
    async def search_with_mcp(self, query: str):
        """Search using MCP server"""
        
        # Configure MCP server parameters with environment variables to suppress logs
        # The open-websearch server outputs logs to stdout, which breaks JSON-RPC protocol
        # Setting these env vars attempts to suppress the informational messages
        env = {
            **os.environ,  # Inherit existing environment
            "NODE_ENV": "production",  # Suppress development logs
            "LOG_LEVEL": "silent",  # Suppress logging output
            "SILENT": "1",  # Alternative silent flag
        }
        
        server_params = StdioServerParameters(
            command="npx",
            args=["--quiet", "open-websearch"],  # --quiet suppresses npx output
            env=env
        )
        
        print(f"🔍 Searching for: '{query}'")
        print("📡 Starting MCP server...")
        
        # Connect to MCP server
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize session
                await session.initialize()
                print("✅ MCP server connected!\n")
                
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
                    messages=messages,
                    tools=anthropic_tools
                )
                
                # Handle tool use
                if response.stop_reason == "tool_use":
                    # Find tool use block
                    tool_use_block = next(
                        block for block in response.content 
                        if block.type == "tool_use"
                    )
                    
                    tool_name = tool_use_block.name
                    tool_input = tool_use_block.input
                    
                    print(f"🔧 Claude is using tool: {tool_name}")
                    print(f"   Input: {tool_input}\n")
                    
                    # Call the MCP tool
                    print("⏳ Fetching search results...\n")
                    tool_result = await session.call_tool(tool_name, tool_input)
                    
                    print("✅ Search results received!\n")
                    
                    # Add to conversation
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_use_block.id,
                            "content": tool_result.content
                        }]
                    })
                    
                    # Get Claude's final answer
                    final_response = self.client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=4096,
                        messages=messages,
                        tools=anthropic_tools
                    )
                    
                    # Extract text
                    for block in final_response.content:
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
                
                else:
                    # Claude answered without using tools
                    for block in response.content:
                        if hasattr(block, "text") and block.text:
                            text = block.text
                            break
                    else:
                        text = "No text response found"
                    print(text)
                    return text
    
    def search(self, query: str):
        """Synchronous wrapper for search_with_mcp"""
        return asyncio.run(self.search_with_mcp(query))


# Test it
if __name__ == "__main__":
    searcher = GymandoSearch()
    
    # Test connection
    searcher.test_connection()
    
    # Search the web
    result = searcher.search("What are the best exercises for lower back pain?")