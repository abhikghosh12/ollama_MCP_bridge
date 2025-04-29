"""
Fallback Agent Module for Google ADK.
This file creates a simple agent with built-in tools that doesn't rely on MCP servers.
"""

import os
import logging
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fallback_agent")

# Set environment variables for Ollama compatibility
os.environ["OPENAI_BASE_URL"] = "http://localhost:11434/v1"
os.environ["OPENAI_API_KEY"] = "unused"
os.environ["OPENAI_API_BASE"] = os.environ["OPENAI_BASE_URL"]

# Choose a model that's good with tool calls
MODEL = "llama3.1"

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

def read_file_content(file_path: str) -> str:
    """Reads and returns the content of a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file_content(file_path: str, content: str) -> str:
    """Writes content to a text file."""
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

def create_dir(directory_path: str) -> str:
    """Creates a new directory."""
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            return f"Successfully created directory: {directory_path}"
        else:
            return f"Directory already exists: {directory_path}"
    except Exception as e:
        return f"Error creating directory: {str(e)}"

def search_for_files(directory_path: str, pattern: str) -> list:
    """Searches for files matching a pattern in the specified directory."""
    import fnmatch
    import os
    
    try:
        if not os.path.isdir(directory_path):
            return [f"Error: {directory_path} is not a valid directory"]
        
        matches = []
        for root, dirnames, filenames in os.walk(directory_path):
            for filename in fnmatch.filter(filenames, pattern):
                matches.append(os.path.join(root, filename))
        
        if not matches:
            return [f"No files matching '{pattern}' found in {directory_path}"]
        
        return matches
    except Exception as e:
        return [f"Error searching for files: {str(e)}"]

# Create fallback agent with built-in tools and export directly as root_agent
root_agent = Agent(
    name="fallback_multi_capability_assistant",
    model=LiteLlm(model=f"openai/{MODEL}"),
    instruction="""You are a helpful assistant with multiple capabilities:

1. You can provide weather information for any city using the 'get_weather' tool.
2. You can work with files and directories:
   * List contents with 'list_files'
   * Read files with 'read_file_content'
   * Write files with 'write_file_content'
   * Create directories with 'create_dir'
   * Find files with 'search_for_files'

Always use the most appropriate tool for each task. When working with files or technical tasks, 
always attempt to use available tools rather than explaining manual steps.

Provide clear, helpful responses and confirm when operations have been completed successfully.
""",
    description="A helpful assistant with file management and weather capabilities.",
    tools=[get_weather, list_files, read_file_content, write_file_content, create_dir, search_for_files],
)

# No async initialization needed as everything is built-in
logger.info("Fallback agent initialized with built-in tools")
logger.info(f"Available tools: {[t.__name__ for t in root_agent.tools]}")
