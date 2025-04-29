"""
Safe MCP tool preparation script that processes servers one by one.
This script connects to each MCP server individually to avoid cascading failures.
"""

import os
import sys
import json
import time
import subprocess
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_tools_prep")

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

# Connect to a single MCP server in a separate process
def connect_to_mcp_server(server_name, server_config):
    """Connect to a single MCP server in a separate process and get its tools."""
    logger.info(f"Connecting to MCP {server_name} server...")
    
    # Create temporary script to connect to this specific server
    script_path = os.path.join(os.path.dirname(__file__), f"temp_connect_{server_name}.py")
    
    with open(script_path, 'w') as f:
        f.write(f"""
import asyncio
import json
import logging
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from contextlib import AsyncExitStack

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("{server_name}_connector")

async def connect_to_server():
    logger.info("Starting connection to {server_name} server")
    
    exit_stack = AsyncExitStack()
    try:
        # Set up connection parameters
        connection_params = StdioServerParameters(
            command="{server_config['command']}",
            args={json.dumps(server_config['args'])},
            env={json.dumps(server_config.get('env', {}))}
        )
        
        # Connect to the server with a timeout
        tools, server_exit_stack = await asyncio.wait_for(
            MCPToolset.from_server(
                connection_params=connection_params,
                async_exit_stack=exit_stack
            ),
            timeout=60  # 60-second timeout
        )
        
        # Get tool schemas
        tool_schemas = []
        for tool in tools:
            try:
                schema = {{
                    "name": tool.name,
                    "description": getattr(tool, "description", ""),
                    "parameters": getattr(tool, "parameters", {{}})
                }}
                tool_schemas.append(schema)
            except Exception as e:
                logger.error(f"Error getting schema for tool: {{e}}")
        
        # Log and return results
        tool_names = [schema["name"] for schema in tool_schemas]
        logger.info(f"Connected to server. Available tools: {{tool_names}}")
        
        # Write results to output file
        with open("{os.path.join(os.path.dirname(__file__), f'temp_result_{server_name}.json')}", 'w') as f:
            json.dump(tool_schemas, f, indent=2)
        
        # Clean up server connection
        await exit_stack.aclose()
        
        logger.info("Connection complete, results saved")
        return True
    
    except Exception as e:
        logger.error(f"Error connecting to server: {{e}}")
        
        # Clean up connection if possible
        try:
            await exit_stack.aclose()
        except Exception:
            pass
        
        return False

if __name__ == "__main__":
    try:
        asyncio.run(connect_to_server())
    except Exception as e:
        logger.error(f"Unhandled exception: {{e}}")
        # Create empty result file to indicate completion even on error
        with open("{os.path.join(os.path.dirname(__file__), f'temp_result_{server_name}.json')}", 'w') as f:
            json.dump([], f)
""")
    
    # Run the script in a separate process with a timeout
    logger.info(f"Starting connection process for {server_name}...")
    result_path = os.path.join(os.path.dirname(__file__), f"temp_result_{server_name}.json")
    
    # Delete existing result file if it exists
    if os.path.exists(result_path):
        try:
            os.remove(result_path)
        except Exception:
            pass
    
    # Run the process with timeout
    process = subprocess.Popen([sys.executable, script_path], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE)
    
    # Wait for up to 2 minutes
    timeout = 120  # seconds
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Check if process has completed
        if process.poll() is not None:
            break
            
        # Check if result file exists
        if os.path.exists(result_path):
            break
            
        # Wait a bit before checking again
        time.sleep(1)
    
    # If process is still running after timeout, kill it
    if process.poll() is None:
        logger.warning(f"Timeout connecting to {server_name} server after {timeout} seconds")
        process.terminate()
        time.sleep(2)
        if process.poll() is None:
            process.kill()
    
    # Read results if available
    if os.path.exists(result_path):
        try:
            with open(result_path, 'r') as f:
                tools = json.load(f)
                logger.info(f"Got {len(tools)} tools from {server_name} server")
                
            # Clean up temporary files
            try:
                os.remove(script_path)
                os.remove(result_path)
            except Exception:
                pass
                
            return tools
        except Exception as e:
            logger.error(f"Error reading results from {server_name} server: {e}")
    else:
        logger.error(f"No results file produced for {server_name} server")
    
    # Clean up temporary script
    try:
        os.remove(script_path)
    except Exception:
        pass
    
    return []

# Process servers in a prioritized order
def process_all_servers(server_names: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Process all specified servers and collect their tools."""
    # Load configuration
    config = load_mcp_config()
    
    # If server_names is empty list or None, use all servers from config
    if not server_names:
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
    
    logger.info(f"Processing {len(server_names)} MCP servers: {', '.join(server_names)}")
    
    # Sort servers by priority
    prioritized_servers = []
    server_names_copy = server_names.copy()
    
    # Define priority tiers
    high_priority = ["filesystem", "server-memory"]
    medium_priority = ["mcp-server-firecrawl", "duckduckgo-mcp-server", "server-github"]
    
    # Add high priority servers
    for name in high_priority:
        if name in server_names_copy:
            prioritized_servers.append(name)
            server_names_copy.remove(name)
    
    # Add medium priority servers
    for name in medium_priority:
        if name in server_names_copy:
            prioritized_servers.append(name)
            server_names_copy.remove(name)
    
    # Add remaining servers
    prioritized_servers.extend(server_names_copy)
    
    logger.info(f"Will process servers in this order: {prioritized_servers}")
    
    # Process each server individually
    all_tools = {}
    for server_name in prioritized_servers:
        if server_name not in config.get('mcpServers', {}):
            logger.warning(f"Server {server_name} not found in configuration, skipping")
            continue
            
        server_config = config['mcpServers'][server_name]
        tools = connect_to_mcp_server(server_name, server_config)
        
        if tools:
            all_tools[server_name] = tools
            logger.info(f"Added {len(tools)} tools from {server_name} server")
        else:
            logger.warning(f"No tools returned from {server_name} server")
    
    # Save all results to the cache file
    try:
        with open(TOOL_CACHE_FILE, 'w') as f:
            json.dump(all_tools, f, indent=2)
            total_tools = sum(len(tools) for tools in all_tools.values())
            logger.info(f"Saved {total_tools} tools from {len(all_tools)} servers to cache file")
    except Exception as e:
        logger.error(f"Error saving tool cache: {e}")
    
    return all_tools

# Main function
def main():
    """Main function to initialize MCP tools."""
    import argparse
    parser = argparse.ArgumentParser(description="Safely initialize MCP tools one by one.")
    parser.add_argument(
        '--servers', 
        nargs='*', 
        help='List of MCP servers to initialize'
    )
    args = parser.parse_args()
    
    # Process all servers
    process_all_servers(args.servers)
    
    logger.info("MCP tools preparation complete. Ready for ADK web.")

if __name__ == "__main__":
    main()
