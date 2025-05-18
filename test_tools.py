#!/usr/bin/env python
"""
Test script to check individual tool functions without MCP protocol overhead.
Run this to verify the tools work correctly.
"""
import sys
import importlib.util
from pathlib import Path

def test_tools():
    print("Testing Periphery MCP Server Tools...")
    
    # Load the server module dynamically
    server_path = Path(__file__).parent / "periphery-mcp-server.py"
    spec = importlib.util.spec_from_file_location("periphery_mcp_server", server_path)
    periphery_mcp_server = importlib.util.module_from_spec(spec)
    
    try:
        spec.loader.exec_module(periphery_mcp_server)
        print("✅ Successfully loaded server module")
    except Exception as e:
        print(f"❌ Failed to load server module: {e}")
        return
    
    # Get the tool functions
    periphery_setup = periphery_mcp_server.periphery_setup
    project_build = periphery_mcp_server.project_build
    periphery_scan = periphery_mcp_server.periphery_scan
    
    # Test 1: Check if we can call a simple tool function
    print("\n--- Test 1: Basic Function Call ---")
    try:
        # This should fail gracefully with a "path does not exist" error
        result = project_build("/nonexistent/path")
        print(f"project_build result: {result}")
        
        if result.get("build_ok") is False and "does not exist" in str(result.get("log_tail", [])):
            print("✅ Tool correctly handles invalid paths")
        else:
            print("❌ Unexpected result for invalid path")
    except Exception as e:
        print(f"❌ Exception calling project_build: {e}")
    
    # Test 2: Test setup function
    print("\n--- Test 2: Setup Function ---")
    try:
        result = periphery_setup("/nonexistent/path")
        print(f"periphery_setup result: {result}")
        
        if result.get("success") is False:
            print("✅ Setup correctly handles invalid paths")
        else:
            print("❌ Setup should fail for nonexistent path")
    except Exception as e:
        print(f"❌ Exception calling periphery_setup: {e}")
    
    # Test 3: Test scan function
    print("\n--- Test 3: Scan Function ---") 
    try:
        result = periphery_scan("/nonexistent/path")
        print(f"periphery_scan result: {result}")
        
        if result.get("build_ok") is False:
            print("✅ Scan correctly handles invalid paths")
        else:
            print("❌ Scan should fail for nonexistent path")
    except Exception as e:
        print(f"❌ Exception calling periphery_scan: {e}")
    
    print("\n--- Summary ---")
    print("If you see ✅ for all tests, the basic tool functions are working correctly.")
    print("To test with a real project, create a test like:")
    print('result = project_build("/path/to/your/ios/project")')
    print("Replace the path with an actual iOS/macOS project directory.")

if __name__ == "__main__":
    test_tools()
