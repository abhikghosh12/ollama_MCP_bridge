"""
Script to initialize MCP tools before starting ADK web.
This script will connect to the MCP servers and initialize the tools.
"""

import os
import sys
import json
import asyncio
import logging
from contextlib import AsyncExitStack
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_tools_prep")

# MCP servers to initialize - leave this list empty to use all from config
# You can also specify specific servers to initialize here
DEFAULT_SERVERS = []

# Exit stacks for each server
exit_stacks = {}

# Tool cache file
TOOL_CACHE_FILE = os.path.join(os.path.dirname(__file__), "mcp_tools_cache.json")

# Load MCP configuration
def load_mcp_config(config_path=None):
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

# Connect to an MCP server and get its tools
async def connect_to_mcp_server(server_name, server_config):
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
        exit_stack = AsyncExitStack()
        try:
            tools, server_exit_stack = await asyncio.wait_for(
                MCPToolset.from_server(
                    connection_params=connection_params,
                    async_exit_stack=exit_stack
                ),
                timeout=30  # 30 second timeout for connecting
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout connecting to MCP {server_name} server after 30 seconds")
            await exit_stack.aclose()
            return []
        
        # Get tool schemas
        tool_schemas = []
        for tool in tools:
            try:
                schema = {
                    "name": tool.name,
                    "description": tool.description if hasattr(tool, "description") else "",
                    "parameters": tool.parameters if hasattr(tool, "parameters") else {},
                }
                tool_schemas.append(schema)
            except Exception as e:
                logger.error(f"Error getting schema for tool {tool}: {e}")
        
        # Log available tools
        tool_names = [schema["name"] for schema in tool_schemas]
        logger.info(f"Connected to MCP {server_name} server. Available tools: {tool_names}")
        
        # Close connection to avoid leaving processes running
        await exit_stack.aclose()
        
        return tool_schemas
    except Exception as e:
        logger.error(f"Error connecting to MCP {server_name} server: {e}")
        return []

# Initialize the MCP tools
async def initialize_mcp_servers(server_names=None):
    """Initialize the MCP servers and cache their tools."""
    # Load configuration
    config = load_mcp_config()
    
    # If server_names is empty list or None, use all servers from config
    if not server_names:  # This handles both None and empty list cases
        server_names = list(config.get('mcpServers', {}).keys())
        logger.info(f"No specific servers provided, using all {len(server_names)} servers from config")
    else:
        # Filter to only include servers that exist in the config
        original_count = len(server_names)
        server_names = [name for name in server_names if name in config.get('mcpServers', {})]
        if len(server_names) < original_count:
            logger.warning(f"Some specified servers were not found in config - using {len(server_names)} valid servers")
    
    if not server_names:
        logger.warning("No MCP servers configured or specified.")
        return {}
    
    logger.info(f"Initializing {len(server_names)} MCP servers: {', '.join(server_names)}")
    
    # Sort servers by priority for better loading order
    prioritized_servers = []
    server_names_copy = server_names.copy()  # Create a copy to avoid modifying during iteration
    
    # Prioritize important servers first
    high_priority = ["filesystem", "server-memory"]
    medium_priority = ["mcp-server-firecrawl", "duckduckgo-mcp-server", "server-github"]
    
    # Add high priority servers first
    for name in high_priority:
        if name in server_names_copy:
            prioritized_servers.append(name)
            server_names_copy.remove(name)
    
    # Add medium priority servers next
    for name in medium_priority:
        if name in server_names_copy:
            prioritized_servers.append(name)
            server_names_copy.remove(name)
    
    # Add remaining servers
    prioritized_servers.extend(server_names_copy)
    
    logger.info(f"Servers will be initialized in this order: {prioritized_servers}")
    
    # Connect to each server and get tools
    all_tools = {}
    for server_name in prioritized_servers:
        server_config = config['mcpServers'][server_name]
        tools = await connect_to_mcp_server(server_name, server_config)
        
        if tools:
            all_tools[server_name] = tools
            logger.info(f"Added {len(tools)} tools from {server_name} server.")
        else:
            logger.warning(f"No tools returned from {server_name} server.")
    
    # Save tools to cache file
    try:
        with open(TOOL_CACHE_FILE, 'w') as f:
            json.dump(all_tools, f, indent=2)
            logger.info(f"Saved {sum(len(tools) for tools in all_tools.values())} tools to cache file")
    except Exception as e:
        logger.error(f"Error saving tool cache: {e}")
    
    return all_tools

# Main function
async def main():
    """Main function to initialize MCP tools."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Initialize MCP tools.")
    parser.add_argument(
        '--servers', 
        nargs='*', 
        help='List of MCP servers to initialize'
    )
    args = parser.parse_args()
    
    # Initialize MCP tools
    server_names = args.servers if args.servers else DEFAULT_SERVERS
    await initialize_mcp_servers(server_names)
    
    logger.info("MCP tools initialization complete. Ready for ADK web.")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
