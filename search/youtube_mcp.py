"""
Gymmando - YouTube MCP Integration
Connects Claude AI with YouTube search via MCP
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class GymmandoYouTubeMCP:
    """
    OOP wrapper for YouTube MCP integration with Claude AI.
    
    Encapsulates the MCP server connection, Claude client, and conversation
    management in a class-based design.
    """
    
    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        youtube_api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096
    ):
        """
        Initialize the Gymmando YouTube MCP client.
        
        Args:
            anthropic_api_key: Anthropic API key (defaults to env var)
            youtube_api_key: YouTube API key (defaults to env var)
            model: Claude model to use
            max_tokens: Maximum tokens for Claude responses
        """
        self.anthropic_api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.youtube_api_key = youtube_api_key or os.environ.get("YOUTUBE_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        
        self._session: Optional[ClientSession] = None
        self._claude_client: Optional[Anthropic] = None
        self._anthropic_tools: List[Dict[str, Any]] = []
        
    def _validate_api_keys(self) -> None:
        """Validate that required API keys are present."""
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        if not self.youtube_api_key:
            raise ValueError("YOUTUBE_API_KEY is required")
    
    def _create_server_params(self) -> StdioServerParameters:
        """Create MCP server parameters for YouTube MCP."""
        return StdioServerParameters(
            command="npx",
            args=["-y", "yt-mcp"],
            env={
                "YOUTUBE_API_KEY": self.youtube_api_key
            }
        )
    
    async def _initialize_mcp_session(self, session: ClientSession) -> None:
        """Initialize the MCP session and load available tools."""
        await session.initialize()
        
        # Get available tools from YouTube MCP
        tools_response = await session.list_tools()
        
        print(f"✓ Connected to YouTube MCP")
        print(f"✓ Available tools: {[tool.name for tool in tools_response.tools]}\n")
        
        # Convert MCP tools to Anthropic format
        self._anthropic_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            }
            for tool in tools_response.tools
        ]
    
    def _initialize_claude_client(self) -> None:
        """Initialize the Claude client."""
        self._claude_client = Anthropic(api_key=self.anthropic_api_key)
    
    async def _handle_tool_use(
        self,
        tool_use_block: Any,
        messages: List[Dict[str, Any]]
    ) -> None:
        """
        Handle a tool use request from Claude.
        
        Args:
            tool_use_block: The tool use block from Claude's response
            messages: Current conversation messages list (modified in-place)
        """
        tool_name = tool_use_block.name
        tool_input = tool_use_block.input
        
        print(f"🔧 Claude is using tool: {tool_name}")
        print(f"   Input: {tool_input}\n")
        
        # Call the MCP tool
        tool_result = await self._session.call_tool(tool_name, tool_input)
        
        print(f"✓ Tool result received\n")
        
        # Add tool result to messages
        # Note: Assistant response is already added in chat() method before this is called
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": tool_result.content
            }]
        })
    
    def _extract_final_text(self, response: Any) -> str:
        """
        Extract final text from Claude's response.
        
        Args:
            response: Claude's response object
            
        Returns:
            The text content from the response
        """
        for block in response.content:
            if hasattr(block, "text") and block.text:
                return block.text
        return ""
    
    async def chat(self, user_message: str) -> str:
        """
        Send a message to Claude that can use YouTube MCP for searching videos.
        
        Args:
            user_message: The user's message/query
            
        Returns:
            Claude's final response text
        """
        self._validate_api_keys()
        
        # Create server parameters
        server_params = self._create_server_params()
        
        # Start MCP server and create session
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self._session = session
                
                # Initialize MCP session
                await self._initialize_mcp_session(session)
                
                # Initialize Claude client
                self._initialize_claude_client()
                
                # Send message to Claude with MCP tools
                print(f"User: {user_message}\n")
                
                messages = [{"role": "user", "content": user_message}]
                
                # Conversation loop to handle tool calls
                while True:
                    response = self._claude_client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        messages=messages,
                        tools=self._anthropic_tools
                    )
                    
                    # Check if Claude wants to use a tool
                    if response.stop_reason == "tool_use":
                        # Extract tool use from response
                        tool_use_block = next(
                            block for block in response.content 
                            if block.type == "tool_use"
                        )
                        
                        # Store the assistant's response before handling tool
                        messages.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        
                        await self._handle_tool_use(tool_use_block, messages)
                        
                        # Continue loop to get Claude's final response
                        continue
                    
                    else:
                        # Claude has finished, print final response
                        final_text = self._extract_final_text(response)
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
    
    # Create Gymmando client instance
    client = GymmandoYouTubeMCP()
    
    # Test queries
    test_queries = [
        "Search YouTube for 'bench press tutorial' and show me the top 3 results",
        "Find me beginner-friendly deadlift form videos",
        "Show me the best squat technique videos"
    ]
    
    # Run first test query
    await client.chat(test_queries[0])
    
    # Uncomment to test more queries:
    # for query in test_queries:
    #     await client.chat(query)
    #     print("\n" + "-"*60 + "\n")


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run async main
    asyncio.run(main())