"""
Enhanced MCP Agent Module for Google ADK.
This file creates a configurable agent that properly integrates multiple MCP servers.
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Tuple, Optional, Any
from contextlib import AsyncExitStack

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("enhanced_mcp_agent")

# Set environment variables for Ollama compatibility
os.environ["OPENAI_BASE_URL"] = "http://localhost:11434/v1"
os.environ["OPENAI_API_KEY"] = "unused"
os.environ["OPENAI_API_BASE"] = os.environ["OPENAI_BASE_URL"]

# Choose a model that's good with tool calls
MODEL = "llama3.1"

# Dictionary to track active connections
active_connections = {}

# Built-in tools
def get_weather(city: str) -> str:
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city (e.g., "New York", "London", "Tokyo").

    Returns:
        str: A report on the current weather in the specified city.
    """
    return f"It is always sunny in {city}!"

def list_files(directory_path: str) -> list:
    """Lists all files in the specified directory."""
    try:
        # Ensure the directory path is valid
        if not os.path.isdir(directory_path):
            return [f"Error: {directory_path} is not a valid directory"]
        
        # Get all files and directories in the path
        files = os.listdir(directory_path)
        
        # Annotate whether each item is a file or directory
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

# Create an instance of the Agent class with basic tools
root_agent = Agent(
    name="multi_capability_assistant",
    model=LiteLlm(model=f"openai/{MODEL}"),
    instruction="""You are a helpful assistant with multiple capabilities:

1. You can provide weather information for any city using the 'get_weather' tool.
2. You can work with files using various filesystem tools.
3. You can search the web if web search tools are available.
4. You can store and retrieve information if memory tools are available.
5. You can interact with GitHub if GitHub tools are available.

Always use the most appropriate tool for each task and provide clear, helpful responses.
""",
    description="A multi-capable assistant with access to various tools and services.",
    tools=[get_weather, list_files],  # Start with basic tools
)

# Function to load MCP configuration
def load_mcp_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load MCP server configuration from a JSON file."""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'mcp_config.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            logger.info(f"Successfully loaded MCP configuration from {config_path}")
            return config
    except Exception as e:
        logger.error(f"Error loading MCP configuration: {e}")
        return {"mcpServers": {}}

# Helper function to categorize a server based on its name
def categorize_server(server_name: str) -> str:
    """Categorize a server based on its name for better logging and prioritization."""
    if 'file' in server_name.lower() or server_name.lower() == 'filesystem':
        return "filesystem"
    elif 'duck' in server_name.lower() or 'search' in server_name.lower() or 'fire' in server_name.lower() or 'crawl' in server_name.lower():
        return "search"
    elif 'memory' in server_name.lower() or 'graph' in server_name.lower():
        return "memory"
    elif 'github' in server_name.lower() or 'git' in server_name.lower():
        return "github"
    elif 'brows' in server_name.lower() or 'play' in server_name.lower():
        return "browser"
    elif 'mail' in server_name.lower() or 'gmail' in server_name.lower():
        return "email"
    elif 'calendar' in server_name.lower() or 'outlook' in server_name.lower():
        return "calendar"
    elif 'airbnb' in server_name.lower():
        return "airbnb"
    elif 'eleven' in server_name.lower():
        return "elevenlabs"
    else:
        return "other"

# Connect to an MCP server and get its tools
async def connect_to_mcp_server(
    server_name: str, 
    server_config: Dict[str, Any],
    exit_stack: AsyncExitStack
) -> List[Any]:
    """Connect to an MCP server and get its tools."""
    logger.info(f"Connecting to MCP {server_name} server...")
    
    try:
        # Create connection parameters
        connection_params = StdioServerParameters(
            command=server_config['command'],
            args=server_config['args'],
            env=server_config.get('env', {})
        )
        
        # Connect to the server and get tools
        tools, server_exit_stack = await MCPToolset.from_server(
            connection_params=connection_params,
            async_exit_stack=exit_stack
        )
        
        # Log available tools
        tool_names = [tool.name for tool in tools]
        logger.info(f"Connected to MCP {server_name} server. Available tools: {tool_names}")
        
        # Track this connection
        active_connections[server_name] = {
            "tools": tools,
            "exit_stack": server_exit_stack
        }
        
        return tools
    except Exception as e:
        logger.error(f"Error connecting to MCP {server_name} server: {e}")
        return []

# Helper function to get server priority based on its category
def get_server_priority(server_category: str) -> int:
    """Get the priority of a server category for initialization order.
    Lower numbers = higher priority.
    """
    priorities = {
        "filesystem": 1,  # Filesystem should be initialized first as it's most basic
        "memory": 2,      # Memory next as it might be used by other tools
        "search": 3,      # Search capabilities
        "github": 4,      # Code repositories
        "browser": 5,     # Web browsing
        "email": 6,       # Email
        "calendar": 7,    # Calendar
        "airbnb": 8,      # Specialized services
        "elevenlabs": 9,  # Media tools
        "other": 10       # Everything else
    }
    return priorities.get(server_category, 100)  # Default to low priority if not found

# Initialize the agent with tools from multiple MCP servers
async def initialize_agent(server_names: Optional[List[str]] = None) -> AsyncExitStack:
    """Initialize the agent with tools from specified MCP servers.
    
    Args:
        server_names: List of server names to initialize. If None, all servers in the config will be used.
        
    Returns:
        AsyncExitStack: The exit stack for managing MCP server connections.
    """
    # Load configuration
    config = load_mcp_config()
    
    # Determine which servers to initialize
    if server_names is None:
        server_names = list(config.get('mcpServers', {}).keys())
    else:
        # Filter to only include servers that exist in the config
        server_names = [name for name in server_names if name in config.get('mcpServers', {})]
    
    if not server_names:
        logger.warning("No MCP servers configured or specified.")
        return AsyncExitStack()
    
    logger.info(f"Initializing {len(server_names)} MCP servers: {', '.join(server_names)}")
    
    # Create an exit stack for managing all connections
    exit_stack = AsyncExitStack()
    
    # Sort servers by priority for better initialization order
    server_with_priority = [(server_name, get_server_priority(categorize_server(server_name))) 
                           for server_name in server_names]
    server_with_priority.sort(key=lambda x: x[1])  # Sort by priority
    sorted_server_names = [server[0] for server in server_with_priority]
    
    logger.info(f"Servers will be initialized in this order: {sorted_server_names}")
    
    # Connect to each server and get tools
    for server_name in sorted_server_names:
        server_config = config['mcpServers'][server_name]
        tools = await connect_to_mcp_server(server_name, server_config, exit_stack)
        
        # Add tools to the agent
        if tools and hasattr(root_agent, 'tools') and isinstance(root_agent.tools, list):
            root_agent.tools.extend(tools)
            logger.info(f"Added {len(tools)} tools from {server_name} server to the agent.")
        else:
            logger.warning(f"Could not add tools from {server_name} - no tools returned or agent issue.")
        # Continue with other servers even if this one failed
    
    # Update the agent's instruction based on available tools
    all_tool_names = set()
    for tool in root_agent.tools:
        if hasattr(tool, 'name'):
            all_tool_names.add(tool.name)
        else:
            # For tools that don't have a name attribute, use their function name if possible
            try:
                if hasattr(tool, '__name__'):
                    all_tool_names.add(tool.__name__)
                elif hasattr(tool, '__class__') and hasattr(tool.__class__, '__name__'):
                    all_tool_names.add(tool.__class__.__name__)
            except Exception as e:
                logger.warning(f"Could not determine name for tool: {tool} - {e}")
                
    logger.info(f"Agent now has access to {len(all_tool_names)} tools: {sorted(all_tool_names)}")
    
    # Enhance agent instruction based on available tools
    enhance_agent_instruction(all_tool_names)
    
    return exit_stack

def enhance_agent_instruction(available_tools: set):
    """Enhance the agent's instruction based on available tools."""
    # Basic instruction parts
    instruction_parts = [
        "You are a helpful assistant with multiple capabilities:"
    ]
    
    # Add weather capability
    if 'get_weather' in available_tools:
        instruction_parts.append("- You can provide weather information for any city using the 'get_weather' tool.")
    
    # Add filesystem capabilities
    filesystem_tools = {'read_file', 'write_file', 'list_directory', 'create_directory', 
                        'search_files', 'get_file_info', 'move_file', 'edit_file'}
    if any(tool in available_tools for tool in filesystem_tools):
        instruction_parts.append("""- You can work with files and directories:
  * List contents with 'list_directory' or 'list_files'
  * Read files with 'read_file'
  * Write or create files with 'write_file'
  * Create directories with 'create_directory'
  * Find files with 'search_files'
  * Get file information with 'get_file_info'
  * Move or rename files with 'move_file'
  * Edit existing files with 'edit_file'""")
    
    # Add web search capabilities
    search_tools = {'search', 'fetch_content', 'firecrawl_search', 'firecrawl_scrape', 'firecrawl_map', 'firecrawl_crawl', 
                  'firecrawl_extract', 'firecrawl_deep_research', 'firecrawl_generate_llmstxt', 'firecrawl_check_crawl_status'}
    if any(tool in available_tools for tool in search_tools):
        instruction_parts.append("- You can search the web for information using search tools like 'search', 'fetch_content', and FireCrawl tools.")
    
    # Add memory capabilities
    memory_tools = {'read_graph', 'search_nodes', 'create_entities', 'create_relations', 'add_observations', 
                  'delete_entities', 'delete_observations', 'delete_relations', 'open_nodes'}
    if any(tool in available_tools for tool in memory_tools):
        instruction_parts.append("- You can store and retrieve information using the memory tools for knowledge graph operations.")
    
    # Add GitHub capabilities
    github_tools = {'search_repositories', 'create_repository', 'get_file_contents', 'create_or_update_file', 
                 'push_files', 'create_issue', 'create_pull_request', 'create_branch', 'fork_repository', 
                 'list_commits', 'list_issues', 'update_issue', 'add_issue_comment', 'search_code', 
                 'search_issues', 'search_users', 'get_issue', 'get_pull_request', 'list_pull_requests', 
                 'create_pull_request_review', 'merge_pull_request', 'get_pull_request_files', 
                 'get_pull_request_status', 'update_pull_request_branch', 'get_pull_request_comments', 'get_pull_request_reviews'}
    if any(tool in available_tools for tool in github_tools):
        instruction_parts.append("- You can interact with GitHub to manage repositories, files, code, issues, and pull requests.")
    
    # Add Browser capabilities
    browser_tools = {'browserbase_create_session', 'browserbase_navigate', 'browserbase_screenshot', 'browserbase_click', 
                   'browserbase_fill', 'browserbase_get_text', 'browser_close', 'browser_wait', 'browser_resize', 
                   'browser_console_messages', 'browser_handle_dialog', 'browser_file_upload', 'browser_install', 
                   'browser_press_key', 'browser_navigate', 'browser_navigate_back', 'browser_navigate_forward', 
                   'browser_network_requests', 'browser_pdf_save', 'browser_snapshot', 'browser_click', 'browser_drag', 
                   'browser_hover', 'browser_type', 'browser_select_option', 'browser_take_screenshot', 'browser_tab_list', 
                   'browser_tab_new', 'browser_tab_select', 'browser_tab_close'}
    if any(tool in available_tools for tool in browser_tools):
        instruction_parts.append("- You can control a web browser to navigate websites, fill forms, click elements, and take screenshots.")
        
    # Add Calendar and Email capabilities
    calendar_tools = {'list_events', 'create_event', 'find_free_slots', 'get_attendee_status', 'delete_event', 
                     'update_event', 'get_calendars'}
    email_tools = {'send_email', 'draft_email', 'read_email', 'search_emails', 'modify_email', 'delete_email', 
                  'list_email_labels', 'batch_modify_emails', 'batch_delete_emails', 'create_label', 'update_label', 
                  'delete_label', 'get_or_create_label'}
    if any(tool in available_tools for tool in calendar_tools):
        instruction_parts.append("- You can manage calendar events, schedule meetings, and find free time slots.")
    if any(tool in available_tools for tool in email_tools):
        instruction_parts.append("- You can send, read, search, and manage emails through Gmail.")
        
    # Add Airbnb capabilities
    airbnb_tools = {'airbnb_search', 'airbnb_listing_details'}
    if any(tool in available_tools for tool in airbnb_tools):
        instruction_parts.append("- You can search for Airbnb listings and get detailed information about specific properties.")
        
    # Add ElevenLabs capabilities
    elevenlabs_tools = {'text_to_speech', 'speech_to_text', 'text_to_sound_effects', 'search_voices', 
                       'get_voice', 'voice_clone', 'isolate_audio', 'check_subscription', 'create_agent', 
                       'add_knowledge_base_to_agent', 'list_agents', 'get_agent', 'speech_to_speech', 
                       'text_to_voice', 'create_voice_from_preview', 'make_outbound_call', 'search_voice_library', 
                       'list_phone_numbers', 'play_audio'}
    if any(tool in available_tools for tool in elevenlabs_tools):
        instruction_parts.append("- You can convert text to speech, speech to text, clone voices, create sound effects, and manage voice agents using ElevenLabs.")
        
    # Final instructions
    instruction_parts.append("""
Always use the most appropriate tool for each task. When working with files or technical tasks, 
always attempt to use available tools rather than explaining manual steps.

Provide clear, helpful responses and confirm when operations have been completed successfully.
""")
    
    # Update the agent's instruction
    root_agent.instruction = "\n".join(instruction_parts)
    logger.info("Updated agent instruction based on available tools")

# Function to gracefully shut down connections
async def shutdown():
    """Gracefully shut down all MCP server connections."""
    logger.info("Shutting down MCP server connections...")
    for server_name, connection in active_connections.items():
        try:
            if 'exit_stack' in connection:
                await connection['exit_stack'].aclose()
                logger.info(f"Closed connection to {server_name} server.")
        except Exception as e:
            logger.error(f"Error closing connection to {server_name} server: {e}")
    
    active_connections.clear()
    logger.info("All MCP server connections closed.")

# Main function for testing
async def main():
    """Test function for the enhanced MCP agent."""
    logger.info("Testing enhanced MCP agent...")
    
    # Initialize with all available servers
    exit_stack = await initialize_agent()
    
    try:
        # Show available tools
        tool_names = [tool.name for tool in root_agent.tools]
        logger.info(f"Agent has {len(tool_names)} tools available: {sorted(tool_names)}")
        
        # Print agent instruction
        logger.info(f"Agent instruction:\n{root_agent.instruction}")
        
        # The agent is now ready to use with ADK web
        logger.info("Agent is ready to use with 'adk web'.")
        
        # In a real application, you would keep the process running here
        # For this test, we'll just wait a bit
        logger.info("Press Ctrl+C to exit...")
        await asyncio.sleep(3600)  # Wait for an hour or until interrupted
    finally:
        # Clean up
        await exit_stack.aclose()
        logger.info("Test completed, all resources cleaned up.")

# Run the initialization if called directly
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        # We can't run asyncio.run() here as we're already in a running event loop
        # In a real application, ensure shutdown() is called on exit
    except Exception as e:
        logger.error(f"Error: {e}")
