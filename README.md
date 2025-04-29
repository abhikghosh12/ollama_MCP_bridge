# Google ADK Agent with MCP Tools

This is a simplified Google Agent Development Kit (ADK) project that demonstrates how to integrate Model Context Protocol (MCP) tools with an ADK agent.

## Project Structure

```
C:\Users\abhik\Documents\google_adk\
│
├── adk_agent\               # Single, unified agent
│   ├── __init__.py
│   ├── agent.py             # Agent with built-in and MCP tools
│   └── .env                 # API key configuration
│
├── README.md                # This documentation
├── setup.bat                # Setup script
├── run_agent.bat            # Run in terminal mode
└── run_web_ui.bat           # Run in web UI mode
```

## Quick Start

1. **Setup the environment**:
   ```
   setup.bat
   ```
   This will create a virtual environment and install the required packages.

2. **Configure API Key**:
   Edit the `.env` file in the `adk_agent` directory and add your Google AI Studio API key.

3. **Run the agent in terminal mode**:
   ```
   run_agent.bat
   ```

4. **Run the agent in web UI mode**:
   ```
   run_web_ui.bat
   ```
   Then open http://localhost:8000 in your browser and select "adk_agent" from the dropdown.

## Features

This agent combines:

1. **Built-in tools**:
   - Real-time weather information for any city worldwide
   - Current local time for any city worldwide

2. **MCP Airbnb tools**:
   - Search for Airbnb listings in any location
   - Get detailed information about Airbnb properties

3. **MCP filesystem tools**:
   - List directories
   - Read files
   - Write files
   - Create directories
   - And more

## How to Use

### For Terminal Mode:

After running `run_agent.bat`, you can interact with the agent directly in the terminal:

- "What's the weather in New Delhi?"
- "What's the current weather in Paris?"
- "What time is it in Tokyo?"
- "Tell me the local time in Singapore"
- "Find Airbnb listings in Miami for next month"
- "Show me Airbnb properties in London for 2 adults"
- "List files in C:\Users\abhik\Documents"
- "Read the content of README.md"
- "Create a directory called test_folder"
- "Write 'Hello World' to a file called test.txt"

Type "exit" to quit the session.

### For Web UI Mode:

After running `run_web_ui.bat`:

1. Open http://localhost:8000 in your browser
2. Select "adk_agent" from the dropdown in the top-left corner
3. Type your queries in the chat box
4. You can also click on function calls to see their details

## Troubleshooting

- **API Key Issues**: Make sure your API key is correctly set in the `.env` file.
- **MCP Tools Not Working**: Make sure Node.js and NPX are installed and in your PATH.
- **Agent Not Visible in Web UI**: Make sure you're running `run_web_ui.bat` from the main directory.
- **Filesystem Permission Issues**: The agent can only access files in the allowed directories.

## How It Works

This project uses a unified approach that:

1. Combines built-in Python functions with MCP tools
2. Properly implements the ADK interface for both terminal and web UI modes
3. Handles MCP server connections with proper cleanup
4. Provides informative feedback during execution

The `agent.py` file is designed to work in multiple contexts:
- As a direct Python script for terminal interaction
- As a web UI agent through the ADK framework
- As a library that can be imported by other applications
