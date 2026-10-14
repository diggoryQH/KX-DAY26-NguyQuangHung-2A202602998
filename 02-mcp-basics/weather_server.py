"""MCP SERVER minh hoạ — công bố tool `get_weather` qua giao thức MCP.

Khác với function calling: tool nằm ở một server ĐỘC LẬP. Server tự "khai
báo" tool của mình; bất kỳ MCP client nào (Claude Code, Claude Desktop,
Cursor, hoặc weather_client.py) cũng cắm vào dùng được mà không cần biết
code bên trong.

Schema của tool được TỰ ĐỘNG sinh ra từ type hints + docstring.

Chạy trực tiếp:
    pip install -r ../requirements.txt
    python weather_server.py

Đăng ký với Claude Code (làm 1 lần, dùng mãi):
    claude mcp add weather -- python /đường/dẫn/tới/weather_server.py
"""

import os
import sys
from pathlib import Path

# Đảm bảo UTF-8 cho Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("weather")

_MOCK_DB = {
    "Hanoi": "29°C, trời mưa",
    "Haiphong": "33°C, mưa rào",
    "Danang": "30°C, nhiều mây",
}


@mcp.tool()
def get_weather(city: str) -> str:
    """Lấy thời tiết hiện tại của một thành phố."""
    if city in _MOCK_DB:
        return f"{city}: {_MOCK_DB[city]}"

    openweather_key = os.getenv("OPENWEATHER_API_KEY")
    if openweather_key:
        try:
            import httpx
            resp = httpx.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": openweather_key, "units": "metric", "lang": "vi"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                temp = round(data["main"]["temp"])
                desc = data["weather"][0]["description"]
                return f"{city}: {temp}°C, {desc} (Live OpenWeatherMap)"
        except Exception:
            pass

    return f"{city}: 28°C, không có dữ liệu chi tiết"


if __name__ == "__main__":
    mcp.run()  # mặc định chạy qua stdio
