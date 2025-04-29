# Enhanced MCP Agent Solution

This package provides an improved implementation of an ADK agent with MCP (Model Context Protocol) integration. It recreates the Claude Desktop MCP configuration and addresses several issues with the original implementation:

1. **Fully compatible with Claude Desktop MCP config** - Uses identical configuration to Claude Desktop
2. **Ensures correct initialization** - Handles asynchronous initialization properly with retries
3. **Integrates multiple MCP servers** - Loads tools from multiple servers in priority order
4. **Provides clean cleanup** - Properly manages exit stacks for MCP connections
5. **Dynamically enhances agent capabilities** - Updates agent instructions based on available tools
6. **Robust error handling** - Continues operation even if some MCP servers fail
7. **Prioritized initialization** - Loads servers in an intelligent order based on dependencies
8. **Fallback capability** - Includes a built-in fallback agent that works without any MCP servers

## Files

- `enhanced_mcp_agent.py` - Main agent implementation with MCP integration
- `mcp_config.json` - Configuration for MCP servers
- `run_enhanced_agent.py` - Launcher script for properly initializing the agent
- `run_enhanced_agent.bat` - Batch file for easy launching on Windows
- `fallback_agent.py` - Fallback agent with built-in tools (no MCP dependencies)
- `__init__.py` - Package initialization

## Usage

### Basic Usage

1. Run the batch file:
   ```
   run_enhanced_agent.bat
   ```

This will initialize all configured MCP servers and start ADK web.

### Specific Servers

To initialize only specific MCP servers:

```
run_enhanced_agent.bat filesystem memory
```

### Safe Mode

To run with only the most reliable MCP servers:

```
run_enhanced_agent.bat --safe
```

### Error Handling

By default, the script will continue even if some servers fail to initialize. To abort on any server failure:

```
run_enhanced_agent.bat --fail-fast
```

### Initialization Retries

To specify the number of initialization retry attempts:

```
run_enhanced_agent.bat --retry 3
```

### Fallback Mode

To skip MCP initialization entirely and use only built-in tools (useful when MCP servers are problematic):

```
run_enhanced_agent.bat --fallback
```

### Initialization Only

To initialize the MCP servers without starting ADK web (useful for testing):

```
run_enhanced_agent.bat --init-only
```

### Combined Options

Options can be combined:

```
run_enhanced_agent.bat filesystem memory --safe --retry 5
```

### Configuration

Edit `mcp_config.json` to add or modify MCP server configurations. Each server configuration requires:

- `command` - The command to run (usually `npx`)
- `args` - Arguments for the command
- `env` (optional) - Environment variables to set

## MCP Servers

The configuration includes all Claude Desktop MCP servers:

1. **filesystem** - File system operations (read, write, search, etc.)
2. **firecrawl** - Web search and crawling capabilities
3. **server-memory** - Persistent memory and knowledge graph
4. **server-github** - GitHub integration (repos, issues, PRs)
5. **duckduckgo-mcp-server** - DuckDuckGo search engine
6. **mcp-server-airbnb** - Airbnb listings search
7. **mcp-browserbase** - Browser automation
8. **playwright-mcp** - Advanced browser automation
9. **server-gmail-autoauth-mcp** - Gmail integration
10. **outlook-calendar-mcp** - Calendar management
11. **ElevenLabs** - Text-to-speech and voice capabilities
12. **mcp-installer** - MCP tool installation utility

## ADK Integration Method

This solution uses Method 1 (ADK as MCP client) from the documentation, where ADK connects to MCP servers using `MCPToolset.from_server()`.

## Troubleshooting

If you encounter issues:

1. Check that all required packages are installed
2. Ensure Ollama is running if using the Ollama integration
3. Check the logs for error messages
4. Verify the paths in the MCP configuration
5. Try running with the `--safe` flag to use only the most reliable servers
6. Increase retries with `--retry 5` for more initialization attempts
7. Examine specific server failures in the logs
8. Make sure npm/npx is correctly installed for MCP servers
9. Check if API keys are correctly configured for services that require them
10. If all else fails, use `--fallback` mode to skip MCP entirely

## Advanced

For advanced usage, you can modify `enhanced_mcp_agent.py` to add more built-in tools or change the agent's behavior.
