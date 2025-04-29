"""
Script to test if MCP tools preparation works properly.
"""

import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_tools")

# Tool cache file
TOOL_CACHE_FILE = os.path.join(os.path.dirname(__file__), "mcp_tools_cache.json")

# Test if the tools cache exists
def test_tool_cache():
    """Test if the tools cache file exists and contains tools."""
    if not os.path.exists(TOOL_CACHE_FILE):
        logger.error(f"Tool cache file not found: {TOOL_CACHE_FILE}")
        return False
    
    try:
        with open(TOOL_CACHE_FILE, 'r') as f:
            tool_cache = json.load(f)
            
            # Check if there are any server entries
            if not tool_cache:
                logger.error("Tool cache is empty")
                return False
            
            # Check each server entry for tools
            for server_name, tools in tool_cache.items():
                logger.info(f"Server '{server_name}' has {len(tools)} tools")
                for i, tool in enumerate(tools[:5]):  # Show at most 5 tools
                    logger.info(f"  Tool {i+1}: {tool.get('name', 'unknown')}")
            
            # Get total tool count
            total_tools = sum(len(tools) for tools in tool_cache.values())
            logger.info(f"Total tools in cache: {total_tools}")
            
            return total_tools > 0
    except Exception as e:
        logger.error(f"Error reading tool cache: {e}")
        return False

if __name__ == "__main__":
    logger.info("Testing MCP tools cache...")
    
    # Test if the tools cache exists and contains tools
    if test_tool_cache():
        logger.info("MCP tools cache test: PASSED")
        print("\nSuccess! Your MCP tools cache is set up correctly.")
        print("You can now run 'start_adk_web.bat' to start ADK web with MCP tools.")
    else:
        logger.error("MCP tools cache test: FAILED")
        print("\nError: MCP tools cache is not set up correctly.")
        print("Please run 'python prepare_mcp_tools.py' to prepare the MCP tools.")
