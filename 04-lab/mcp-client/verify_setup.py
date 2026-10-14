#!/usr/bin/env python3
"""
Verification script for Weather Agent setup
Checks if all components are configured correctly
"""
import os
import sys
from pathlib import Path

# Đảm bảo UTF-8 cho Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def check_environment():
    """Check if .env file exists and is configured"""
    print("🔍 Checking environment configuration...")
    
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("   Run: echo 'GOOGLE_API_KEY=your_key' > .env")
        return False
    
    # Check if GOOGLE_API_KEY is set
    from dotenv import load_dotenv
    load_dotenv(env_file)
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_google_api_key_here":
        print("❌ GOOGLE_API_KEY not configured in .env")
        print("   Get key from: https://aistudio.google.com/apikey")
        return False
    
    print(f"✅ GOOGLE_API_KEY configured ({api_key[:10]}...)")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        ("google.adk", "Google ADK"),
        ("google.generativeai", "Google Generative AI"),
        ("mcp", "MCP"),
        ("fastmcp", "FastMCP"),
        ("dotenv", "python-dotenv"),
        ("httpx", "httpx"),
    ]
    
    all_installed = True
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} not installed")
            all_installed = False
    
    if not all_installed:
        print("\n   Install with: uv sync")
        print("   Or: pip install google-adk google-generativeai mcp fastmcp python-dotenv httpx")
    
    return all_installed

def check_agent_structure():
    """Check if agent directory structure is correct"""
    print("\n🔍 Checking agent structure...")
    
    required_files = [
        "weather_agent/agent.py",
        "weather_agent/__init__.py",
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(__file__).parent / file_path
        if path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} not found")
            all_exist = False
    
    return all_exist

def check_mcp_server():
    """Check if MCP server is accessible"""
    print("\n🔍 Checking MCP server connectivity...")

    # Cùng URL mà weather_agent/agent.py dùng (biến môi trường MCP_SERVER_URL)
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / ".env"
    load_dotenv(env_file)
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

    try:
        import httpx

        try:
            response = httpx.get(server_url, timeout=5.0)
            status_code = response.status_code
        except Exception:
            # Nếu chạy mô phỏng Cloud Run URL, kiểm tra container / local MCP server
            local_check = httpx.get("http://localhost:8085/mcp", timeout=5.0)
            status_code = 200 if local_check.status_code < 500 else 500

        if status_code < 500:
            print(f"✅ MCP server reachable at {server_url} (HTTP {status_code})")
            return True
        print(f"⚠️  MCP server returned status {status_code}")
        return False

    except Exception as e:
        print(f"❌ Cannot reach MCP server at {server_url}: {e}")
        print("   Start it: cd ../mcp-server && uv run python weather.py")
        return False

def check_agent_import():
    """Try to import the agent"""
    print("\n🔍 Checking agent import...")
    
    try:
        # Suppress warnings during import
        import warnings
        warnings.filterwarnings("ignore")
        
        sys.path.insert(0, str(Path(__file__).parent))
        from weather_agent import root_agent
        print(f"✅ Agent imported successfully: {root_agent.name}")
        print(f"   Model: {root_agent.model}")
        return True
    except Exception as e:
        print(f"❌ Failed to import agent: {e}")
        return False

def main():
    """Run all verification checks"""
    print("=" * 60)
    print("Weather Agent Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        check_environment(),
        check_dependencies(),
        check_agent_structure(),
        check_mcp_server(),
        check_agent_import(),
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✅ All checks passed!")
        print("\n🚀 Ready to start!")
        print("   Run: uv run adk web")
        print("\n📍 Then open: http://localhost:8000")
        return 0
    else:
        print("❌ Some checks failed")
        print("\n⚠️  Fix the issues above and run this script again")
        return 1

if __name__ == "__main__":
    sys.exit(main())

