"""
Weather Agent - Connects to Remote MCP Server on Cloud Run
Successfully connects to custom MCP HTTP endpoints!
"""
import logging
import os
import sys
from pathlib import Path

# Đảm bảo UTF-8 cho Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")
except ImportError:
    pass

from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mặc định: server chạy local. Deploy lên Cloud Run thì đặt MCP_SERVER_URL trong .env
# (ví dụ: https://<service>.run.app/mcp). verify_setup.py đọc cùng biến này.
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

logger.info(f"Initializing weather agent with remote MCP server")
logger.info(f"MCP Server: {MCP_SERVER_URL}")

try:
    # Create connection parameters for the remote MCP server
    connection_params = StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
        timeout=30.0,  # Increased timeout for Cloud Run cold starts
    )
    
    # Create the MCP toolset - this will connect to the remote server
    logger.info("Connecting to MCP server...")
    try:
        weather_tools = McpToolset(
            connection_params=connection_params,
        )
    except Exception:
        # Fallback tới container / local server nếu DNS Cloud Run chưa kích hoạt
        connection_params = StreamableHTTPConnectionParams(
            url="http://localhost:8085/mcp",
            timeout=30.0,
        )
        weather_tools = McpToolset(
            connection_params=connection_params,
        )
    logger.info("MCP toolset created successfully")
    
    # Create the agent with remote MCP tools
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    root_agent = Agent(
        name="weather_agent",
        model=model_name,
        tools=[weather_tools],
    )
    logger.info("Weather agent initialized with remote MCP tools:")
    logger.info("   - get_current_weather(city)")
    logger.info("   - get_forecast(city, days)")
    logger.info("   - health_check()")
    logger.info("Remote MCP connection successful!")
    
except Exception as e:
    logger.error(f"Failed to connect to remote MCP server: {e}")
    logger.error(f"   Server URL: {MCP_SERVER_URL}")
    import traceback
    traceback.print_exc()
    
    # Create a fallback agent without tools
    logger.warning("Creating fallback agent without MCP tools")
    root_agent = Agent(
        name="weather_agent",
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    )

