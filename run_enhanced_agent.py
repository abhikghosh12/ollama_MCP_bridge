"""
Launcher script for the enhanced MCP agent.
This script properly initializes the MCP agent with specified servers before starting ADK web.
"""

import os
import sys
import asyncio
import argparse
import logging
import subprocess
import time
import importlib
from typing import List, Optional, Dict, Any
from contextlib import AsyncExitStack

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_launcher")

# Import the enhanced MCP agent
from enhanced_mcp_agent import initialize_agent, load_mcp_config

async def initialize_and_prepare(server_names: Optional[List[str]] = None, ignore_errors: bool = True, max_retries: int = 2) -> AsyncExitStack:
    """Initialize the MCP agent with specified servers."""
    logger.info("Initializing enhanced MCP agent...")
    
    # If no servers specified, list all available servers
    if not server_names:
        config = load_mcp_config()
        available_servers = list(config.get('mcpServers', {}).keys())
        logger.info(f"Available MCP servers: {', '.join(available_servers)}")
        
        # Use all available servers if none specified
        server_names = available_servers
        
    # Filter out any servers that might cause issues
    if ignore_errors and not server_names:
        logger.warning("No servers specified. Will use a minimal set of reliable servers.")
        # Use only the most reliable servers if none specified
        default_servers = ['filesystem', 'server-memory']
        server_names = [name for name in default_servers if name in available_servers]
    
    # Initialize the agent with retries
    exit_stack = None
    retry_count = 0
    last_error = None
    
    while retry_count <= max_retries:
        try:
            # Try to initialize
            exit_stack = await initialize_agent(server_names)
            # If successful, break out of retry loop
            logger.info(f"Successfully initialized agent on attempt {retry_count + 1}")
            break
        except Exception as e:
            last_error = e
            retry_count += 1
            logger.warning(f"Error initializing agent (attempt {retry_count}/{max_retries+1}): {e}")
            
            if retry_count <= max_retries:
                # Wait before retrying (increasing backoff)
                wait_time = 2 ** retry_count
                logger.info(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
    
    # If we exhausted all retries and still failed
    if exit_stack is None:
        if ignore_errors:
            logger.warning("Failed to initialize agent after retries, switching to fallback agent...")
            # Try to import the fallback agent
            try:
                import fallback_agent
                logger.info("Successfully imported fallback agent with built-in tools")
                from fallback_agent import root_agent as fallback_root_agent
                
                # Import the enhanced_mcp_agent module to replace its root_agent
                import enhanced_mcp_agent
                enhanced_mcp_agent.root_agent = fallback_root_agent
                
                logger.info("Replaced MCP agent with fallback agent - continuing with built-in tools only")
                # Create an empty exit stack to return
                exit_stack = AsyncExitStack()
            except Exception as e:
                logger.error(f"Error loading fallback agent: {e}")
                # Create an empty exit stack anyway
                exit_stack = AsyncExitStack()
        else:
            logger.error(f"Failed to initialize agent after {max_retries+1} attempts: {last_error}")
            raise last_error
    
    # We don't await exit_stack.aclose() here since we want to keep the connections open
    # The connections will be closed when the process exits
    logger.info("Enhanced MCP agent initialized successfully.")
    logger.info(f"Initialized servers: {', '.join(server_names)}")
    
    # Return the exit stack (though it won't be used in this script)
    return exit_stack

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Launch enhanced MCP agent with ADK web.")
    parser.add_argument(
        '--servers', 
        nargs='*', 
        help='List of MCP servers to initialize (e.g., filesystem memory github)'
    )
    parser.add_argument(
        '--config', 
        help='Path to MCP configuration file'
    )
    parser.add_argument(
        '--init-only', 
        action='store_true',
        help='Only initialize the agent without starting ADK web'
    )
    parser.add_argument(
        '--fail-fast',
        action='store_true',
        help='Exit on first error instead of ignoring problematic servers'
    )
    parser.add_argument(
        '--retry',
        type=int,
        default=2,
        help='Number of retries for initialization (default: 2)'
    )
    parser.add_argument(
        '--safe-mode',
        action='store_true',
        help='Use only essential servers known to be reliable'
    )
    parser.add_argument(
        '--fallback-only',
        action='store_true',
        help='Skip MCP initialization and use only built-in tools'
    )
    return parser.parse_args()

def launch_adk_web():
    """Launch ADK web server."""
    logger.info("Starting ADK web server...")
    
    try:
        # Determine the path to the adk command
        adk_command = "adk"
        if sys.platform == "win32":
            # On Windows, check if we need to use adk.exe
            if os.path.exists(os.path.join(sys.prefix, 'Scripts', 'adk.exe')):
                adk_command = os.path.join(sys.prefix, 'Scripts', 'adk.exe')
        
        # Run ADK web
        subprocess.run([adk_command, "web"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running ADK web: {e}")
        sys.exit(1)
    except FileNotFoundError:
        logger.error("ADK command not found. Make sure ADK is installed and in your PATH.")
        sys.exit(1)

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Create an asyncio event loop
    loop = asyncio.get_event_loop()
    
    try:
        # If fallback-only is specified, use the fallback agent instead of MCP
        if args.fallback_only:
            logger.info("Fallback-only mode enabled - using built-in tools only")
            try:
                import fallback_agent
                from fallback_agent import root_agent as fallback_root_agent
                
                # Import the enhanced_mcp_agent module to replace its root_agent
                import enhanced_mcp_agent
                enhanced_mcp_agent.root_agent = fallback_root_agent
                
                logger.info("Successfully initialized fallback agent")
                exit_stack = AsyncExitStack()
            except Exception as e:
                logger.error(f"Error loading fallback agent: {e}")
                sys.exit(1)
        else:
            # Determine server names to use
            server_names = args.servers if args.servers else None
        
        # If safe mode is enabled, use only reliable servers
        if args.safe_mode:
            logger.info("Safe mode enabled - using only essential servers")
            safe_servers = ['filesystem', 'server-memory']
            if server_names:
                # Filter the requested servers to only include safe ones
                server_names = [name for name in server_names if name in safe_servers]
                if not server_names:
                    # If none of the requested servers are safe, use the default safe servers
                    server_names = safe_servers
                    logger.warning("None of the requested servers are considered safe. Using default safe servers.")
            else:
                server_names = safe_servers
        
        # Initialize the agent
        ignore_errors = not args.fail_fast  # Invert the fail-fast flag
        exit_stack = loop.run_until_complete(
            initialize_and_prepare(
                server_names=server_names,
                ignore_errors=ignore_errors,
                max_retries=args.retry
            )
        )
        
        # Start ADK web if not in init-only mode
        if not args.init_only:
            launch_adk_web()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
