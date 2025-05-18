# Periphery MCP Server

A Model Context Protocol (MCP) server that exposes [Periphery](https://github.com/peripheryapp/periphery) static analysis capabilities for iOS/macOS projects through a simple HTTP API.

## Overview

This server wraps Periphery's dead code detection functionality, making it accessible to MCP clients like Claude Desktop. It provides automated setup, build verification, and comprehensive static analysis scanning for Swift/Objective-C projects.

## Features

- **Automated Setup**: Interactive Periphery configuration with sensible defaults
- **Build Verification**: Pre-scan build validation to catch issues early
- **Structured Analysis**: JSON-formatted scan results with detailed issue reporting
- **Error Handling**: Comprehensive error reporting with actionable feedback
- **MCP Integration**: Seamless integration with Claude Desktop and other MCP clients

## Prerequisites

- **macOS**: Required for Xcode and iOS/macOS development
- **Xcode**: For building iOS/macOS projects
- **Periphery**: Install via Homebrew: `brew install peripheryapp/periphery/periphery`
- **Python 3.8+**: For running the MCP server

## Installation

1. **Clone or download** this repository
2. **Create a conda environment**:
   ```bash
   conda create -n periphery-mcp python=3.12
   conda activate periphery-mcp
   ```
3. **Install dependencies**:
   ```bash
   pip install 'mcp[cli]==1.*' fastapi uvicorn pexpect rich
   ```

## Usage

### Starting the Server

```bash
cd /path/to/periphery-mcp
conda activate periphery-mcp
python periphery-mcp-server.py
```

The server will start on `http://localhost:4000` and provide the following endpoints:
- `/mcp/metadata` - Server capabilities and tool definitions
- `/mcp/invoke/<tool>` - Tool execution endpoints

### Available Tools

#### 1. `periphery_setup`
Runs Periphery's interactive setup wizard to create a `.periphery.yml` configuration file.

**Parameters:**
- `project_path` (string): Path to your Xcode project directory

**Returns:**
- `success` (boolean): Whether setup completed successfully
- `yml` (string|null): Generated YAML configuration
- `log_tail` (array): Setup process log output

#### 2. `project_build`
Verifies that the project builds successfully before running static analysis.

**Parameters:**
- `project_path` (string): Path to your Xcode project directory
- `scheme` (string, optional): Xcode scheme to build

**Returns:**
- `build_ok` (boolean): Whether build succeeded
- `log_tail` (array): Build error messages (if any)

#### 3. `periphery_scan`
Performs comprehensive static analysis to detect unused code.

**Parameters:**
- `project_path` (string): Path to your Xcode project directory
- `extra_args` (array, optional): Additional Periphery command-line arguments

**Returns:**
- `build_ok` (boolean): Whether the scan completed successfully
- `issues` (array): Detected issues with location information
- `raw_json` (object|null): Full Periphery output in JSON format
- `build_error` (object|null): Error details if scan failed

### Example Issue Format

```json
{
  "kind": "unused_function",
  "identifier": "MyClass.unusedMethod()",
  "file": "/path/to/MyClass.swift",
  "line": 42
}
```

## Integration with Claude Desktop

To use this server with Claude Desktop:

1. **Start the server** as shown above
2. **Configure Claude Desktop** to connect to `http://localhost:4000`
3. **Use natural language** to analyze your projects:
   - "Scan my iOS project for dead code"
   - "Check if my project builds successfully"
   - "Set up Periphery for my new Swift project"

## Workflow Example

1. **Setup**: First run creates `.periphery.yml` with project-specific configuration
2. **Build Check**: Verifies project compiles successfully
3. **Scan**: Analyzes code for unused declarations, imports, and protocols
4. **Review**: Examine results and remove identified dead code

## Configuration

The server automatically handles Periphery configuration through interactive setup. Common configuration options include:

- **Build targets**: Which schemes/targets to analyze
- **File patterns**: Include/exclude specific files or directories
- **Analysis depth**: How thorough the static analysis should be

## Troubleshooting

### Common Issues

**"Periphery setup failed"**
- Ensure your project builds successfully in Xcode
- Check that all dependencies are properly configured
- Verify Periphery is installed: `periphery version`

**"Build failed"**
- Open project in Xcode and resolve any compilation errors
- Ensure all required certificates and provisioning profiles are available
- Check that the specified scheme exists

**Connection refused**
- Verify the server is running: `curl http://localhost:4000/mcp/metadata`
- Check that port 4000 isn't blocked by firewall
- Ensure conda environment is activated

### Debug Mode

For detailed logging, run with debug output:
```bash
PYTHONPATH=. python periphery-mcp-server.py --log-level debug
```

## Limitations

- **Platform**: macOS only (due to Xcode dependency)
- **Interactive Setup**: Simplified prompt handling (uses defaults for complex prompts)
- **Build Requirements**: Project must compile successfully for analysis

## Contributing

Contributions welcome! Areas for improvement:

- Enhanced interactive setup with full streaming support
- Support for additional static analysis tools
- Integration with CI/CD pipelines
- More granular filtering options

## License

This project is provided as-is for educational and development purposes.

## Related Projects

- [Periphery](https://github.com/peripheryapp/periphery) - The underlying static analysis tool
- [Model Context Protocol](https://github.com/modelcontextprotocol/python-sdk) - The protocol specification
- [Claude Desktop](https://claude.ai/desktop) - MCP client for AI-assisted development