"""
Agent module for ADK web integration with MCP tools.
This file creates an instance of Agent for use with ADK web.
"""

import os
import logging
import json
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_agent")

# Import from fallback_agent but catch any errors
try:
    from .fallback_agent import root_agent as fallback_root_agent
    logger.info("Successfully imported fallback agent")
except Exception as e:
    logger.error(f"Error importing fallback agent: {e}")
    fallback_root_agent = None

# Check if MCP tools cache exists and load it
TOOL_CACHE_FILE = os.path.join(os.path.dirname(__file__), "mcp_tools_cache.json")

# Function to create an MCP tool factory
def create_mcp_tool_factory(tool_schema):
    """Create a function that simulates an MCP tool."""
    tool_name = tool_schema.get("name", "unknown_tool")
    tool_description = tool_schema.get("description", f"MCP tool: {tool_name}")
    
    def mcp_tool(**kwargs):
        """MCP tool function that returns a formatted result."""
        # This is just a placeholder that would normally call the actual MCP tool
        args_str = ", ".join(f"{k}='{v}'" for k, v in kwargs.items())
        logger.info(f"MCP tool '{tool_name}' called with args: {args_str}")
        return f"MCP tool '{tool_name}' executed with arguments: {kwargs}"
    
    # Set name and docstring
    mcp_tool.__name__ = tool_name
    mcp_tool.__doc__ = tool_description
    
    return mcp_tool

# Try to load MCP tools from cache
mcp_tools = []
try:
    if os.path.exists(TOOL_CACHE_FILE):
        with open(TOOL_CACHE_FILE, 'r') as f:
            tool_cache = json.load(f)
            logger.info(f"Loaded MCP tools cache with {len(tool_cache)} server entries")
            
            # Create tools from cache
            for server_name, tools in tool_cache.items():
                for tool_schema in tools:
                    try:
                        tool_factory = create_mcp_tool_factory(tool_schema)
                        mcp_tools.append(tool_factory)
                        logger.info(f"Created MCP tool factory for {tool_schema.get('name', 'unknown')}")
                    except Exception as e:
                        logger.error(f"Error creating tool factory: {e}")
    else:
        logger.warning(f"MCP tools cache file not found at {TOOL_CACHE_FILE}")
except Exception as e:
    logger.error(f"Error loading MCP tools cache: {e}")

# Set environment variables for Ollama compatibility
os.environ["OPENAI_BASE_URL"] = "http://localhost:11434/v1"
os.environ["OPENAI_API_KEY"] = "unused"
os.environ["OPENAI_API_BASE"] = os.environ["OPENAI_BASE_URL"]

# Choose a model that's good with tool calls
MODEL = "llama3.1"

# Basic tools for the minimal agent
def get_weather(city: str) -> str:
    """Retrieves the current weather report for a specified city."""
    return f"It is always sunny in {city}!"

def list_files(directory_path: str) -> list:
    """Lists all files in the specified directory."""
    try:
        if not os.path.isdir(directory_path):
            return [f"Error: {directory_path} is not a valid directory"]
        
        files = os.listdir(directory_path)
        
        annotated_files = []
        for item in files:
            full_path = os.path.join(directory_path, item)
            if os.path.isfile(full_path):
                annotated_files.append(f"[FILE] {item}")
            elif os.path.isdir(full_path):
                annotated_files.append(f"[DIR] {item}")
        
        return annotated_files
    except Exception as e:
        return [f"Error listing files: {str(e)}"]

# Create tool list with basic and MCP tools
tool_list = [get_weather, list_files]

# Add MCP tools if available
if mcp_tools:
    tool_list.extend(mcp_tools)
    logger.info(f"Added {len(mcp_tools)} MCP tools to tool list")
else:
    logger.warning("No MCP tools available, using only basic tools")
    # If fallback_agent has more tools, use those
    if fallback_root_agent is not None and hasattr(fallback_root_agent, 'tools'):
        tool_list = fallback_root_agent.tools
        logger.info("Using tools from fallback agent")

# Create the enhanced agent with all available tools
root_agent = Agent(
    name="mcp_enhanced_assistant",
    model=LiteLlm(model=f"openai/{MODEL}"),
    instruction="""You are a helpful assistant with multiple capabilities including weather information and more.

You have access to the following tools:
- Weather information for any city
- File system operations (list, read, write, create, search)
- Additional MCP tools if they are available

Always use the most appropriate tool for each task. When working with files or technical tasks,
always attempt to use available tools rather than explaining manual steps.

Provide clear, helpful responses and confirm when operations have been completed successfully.
""",
    description="A multi-capable assistant with access to various tools and services.",
    tools=tool_list,
)

# Log the available tools
logger.info(f"Agent initialized with {len(tool_list)} tools")
tool_names = []
for tool in tool_list:
    try:
        if hasattr(tool, 'name'):
            tool_names.append(tool.name)
        elif hasattr(tool, '__name__'):
            tool_names.append(tool.__name__)
        else:
            tool_names.append("unknown_tool")
    except Exception:
        pass
logger.info(f"Available tools: {sorted(tool_names)}")
