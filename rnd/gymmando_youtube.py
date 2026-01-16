"""
Gymmando - YouTube MCP Integration
Connects Claude AI with YouTube search via MCP
"""

import os
import asyncio
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def chat_with_youtube_mcp(user_message: str):
    """
    Send a message to Claude that can use YouTube MCP for searching videos
    """
    
    # Configure YouTube MCP server
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "yt-mcp"],
        env={
            "YOUTUBE_API_KEY": os.environ.get("YOUTUBE_API_KEY")
        }
    )
    
    # Start MCP server and create session
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize MCP session
            await session.initialize()
            
            # Get available tools from YouTube MCP
            tools_response = await session.list_tools()
            
            print(f"✓ Connected to YouTube MCP")
            print(f"✓ Available tools: {[tool.name for tool in tools_response.tools]}\n")
            
            # Initialize Claude client
            client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            
            # Convert MCP tools to Anthropic format
            anthropic_tools = []
            for tool in tools_response.tools:
                anthropic_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
            
            # Send message to Claude with MCP tools
            print(f"User: {user_message}\n")
            
            messages = [{"role": "user", "content": user_message}]
            
            # Conversation loop to handle tool calls
            while True:
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    messages=messages,
                    tools=anthropic_tools
                )
                
                # Check if Claude wants to use a tool
                if response.stop_reason == "tool_use":
                    # Extract tool use from response
                    tool_use_block = next(
                        block for block in response.content 
                        if block.type == "tool_use"
                    )
                    
                    tool_name = tool_use_block.name
                    tool_input = tool_use_block.input
                    
                    print(f"🔧 Claude is using tool: {tool_name}")
                    print(f"   Input: {tool_input}\n")
                    
                    # Call the MCP tool
                    tool_result = await session.call_tool(tool_name, tool_input)
                    
                    print(f"✓ Tool result received\n")
                    
                    # Add assistant response and tool result to messages
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
                    
                    # Continue loop to get Claude's final response
                    continue
                
                else:
                    # Claude has finished, print final response
                    final_text = next(
                        block.text for block in response.content 
                        if hasattr(block, "text")
                    )
                    print(f"Claude: {final_text}\n")
                    return final_text


async def main():
    """
    Main function to test YouTube MCP integration
    """
    print("="*60)
    print("GYMMANDO - YouTube MCP Integration Test")
    print("="*60)
    print()
    
    # Check environment variables
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not found in environment")
        return
    
    if not os.environ.get("YOUTUBE_API_KEY"):
        print("❌ YOUTUBE_API_KEY not found in environment")
        return
    
    print("✓ API keys loaded\n")
    
    # Test queries
    test_queries = [
        "Search YouTube for 'bench press tutorial' and show me the top 3 results",
        "Find me beginner-friendly deadlift form videos",
        "Show me the best squat technique videos"
    ]
    
    # Run first test query
    await chat_with_youtube_mcp(test_queries[0])
    
    # Uncomment to test more queries:
    # for query in test_queries:
    #     await chat_with_youtube_mcp(query)
    #     print("\n" + "-"*60 + "\n")


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run async main
    asyncio.run(main())