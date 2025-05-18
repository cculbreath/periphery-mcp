#!/usr/bin/env python
"""
Command-line interface for testing Periphery MCP tools.
Usage:
    python cli_test.py scan /path/to/project
    python cli_test.py build /path/to/project [scheme]
    python cli_test.py setup /path/to/project
"""
import sys
import json
import importlib.util
from pathlib import Path

def load_server_module():
    """Load the server module to access tool functions."""
    server_path = Path(__file__).parent / "periphery-mcp-server.py"
    spec = importlib.util.spec_from_file_location("periphery_mcp_server", server_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def pretty_print_result(result):
    """Pretty print the tool result."""
    if isinstance(result, dict):
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result)

def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python cli_test.py scan /path/to/project [extra_args...]")
        print("  python cli_test.py build /path/to/project [scheme]")
        print("  python cli_test.py setup /path/to/project")
        print("\nExamples:")
        print("  python cli_test.py scan ~/MyProject")
        print("  python cli_test.py scan ~/MyProject --verbose")
        print("  python cli_test.py build ~/MyProject MyApp")
        print("  python cli_test.py setup ~/MyProject")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    project_path = sys.argv[2]
    
    # Load the server module
    try:
        server = load_server_module()
        print(f"✅ Loaded Periphery MCP server module")
    except Exception as e:
        print(f"❌ Failed to load server module: {e}")
        sys.exit(1)
    
    print(f"Running '{command}' on project: {project_path}\n")
    
    # Execute the requested command
    try:
        if command == "scan":
            extra_args = sys.argv[3:] if len(sys.argv) > 3 else None
            result = server.periphery_scan(project_path, extra_args)
        elif command == "build":
            scheme = sys.argv[3] if len(sys.argv) > 3 else None
            result = server.project_build(project_path, scheme)
        elif command == "setup":
            result = server.periphery_setup(project_path)
        else:
            print(f"❌ Unknown command: {command}")
            print("Valid commands: scan, build, setup")
            sys.exit(1)
        
        print("Result:")
        pretty_print_result(result)
        
        # Summary
        if command == "scan":
            if result.get("build_ok"):
                issues = result.get("issues", [])
                print(f"\n✅ Scan completed successfully. Found {len(issues)} issues.")
                if issues:
                    print("Issues found:")
                    for issue in issues[:5]:  # Show first 5 issues
                        print(f"  - {issue['kind']}: {issue['identifier']} ({issue['file']}:{issue['line']})")
                    if len(issues) > 5:
                        print(f"  ... and {len(issues) - 5} more issues")
            else:
                print("❌ Scan failed. Check the error details above.")
        elif command == "build":
            if result.get("build_ok"):
                print("\n✅ Build completed successfully.")
            else:
                print("❌ Build failed. Check the error details above.")
        elif command == "setup":
            if result.get("success"):
                print("\n✅ Setup completed successfully.")
                if result.get("yml"):
                    print("Generated configuration:")
                    print(result["yml"])
            else:
                print("❌ Setup failed. Check the error details above.")
                
    except Exception as e:
        print(f"❌ Error executing {command}: {e}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
