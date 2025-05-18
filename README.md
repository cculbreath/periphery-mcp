# Periphery MCP Server

A Model Context Protocol (MCP) server that exposes [Periphery](https://github.com/peripheryapp/periphery) static analysis capabilities for iOS/macOS projects through the **Model Context Protocol over a standard input/output (stdio) transport**.

## Overview

This server wraps Periphery's dead-code-detection functionality, making it accessible to MCP-aware clients such as Claude Desktop.  Communication happens entirely over MCP's stdio transport—**no HTTP server is started or exposed**.  The server provides automated setup, build verification, and comprehensive static-analysis scanning for Swift/Objective-C projects.

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
   pip install "mcp[cli]==1.*" pexpect rich
   ```

## Usage

### Starting the Server

The server runs as an MCP stdio transport (for integration with Claude Desktop):

```bash
cd /path/to/periphery-mcp
conda activate periphery-mcp
python periphery-mcp-server.py
```

When integrated with Claude Desktop, the server communicates over stdin/stdout. For standalone testing, you can use the MCP CLI tools.

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

To use this server with Claude Desktop, you need to add it to your MCP configuration:

### Step 1: Add to Claude Desktop Configuration

Edit your Claude Desktop configuration file (located at `~/Library/Application Support/Claude/claude_desktop_config.json`) and add the following entry to the `mcpServers` section:

```json
{
  "mcpServers": {
    "periphery-mcp": {
      "command": "/path/to/conda/envs/periphery-mcp/bin/python",
      "args": [
        "/path/to/periphery-mcp/periphery-mcp-server.py"
      ],
      "env": {
        "CONDA_DEFAULT_ENV": "periphery-mcp"
      }
    }
  }
}
```

**Replace the paths** with your actual installation paths:
- `/path/to/conda/envs/periphery-mcp/bin/python` → Your conda environment Python executable
- `/path/to/periphery-mcp/periphery-mcp-server.py` → Path to this server script

### Step 2: Find Your Python Path

To find your conda environment Python path:
```bash
conda activate periphery-mcp
which python
```

### Step 3: Restart Claude Desktop

After updating the configuration, restart Claude Desktop for the changes to take effect.

### Step 4: Use Natural Language Commands

Once configured, you can use natural language to analyze your projects:
- "Scan my iOS project for dead code"
- "Check if my project builds successfully"
- "Set up Periphery for my new Swift project"

### Alternative: Using the Included Startup Script

For easier configuration, you can use the included startup script that automatically detects your conda installation:

```bash
chmod +x start-server.sh
./start-server.sh
```

The startup script will:
- Automatically detect common conda installation locations
- Change to the correct directory
- Activate the periphery-mcp environment
- Start the server

Then use this simpler Claude Desktop configuration:
```json
{
  "mcpServers": {
    "periphery-mcp": {
      "command": "/absolute/path/to/periphery-mcp/start-server.sh"
    }
  }
}
```

Replace `/absolute/path/to/periphery-mcp/` with the actual path to your project directory.

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

### Command-Line Testing

You can test the tools directly from the command line without Claude Desktop:

```bash
# Test scanning a project
python cli_test.py scan /path/to/your/ios/project

# Test building a project (optionally specify scheme)
python cli_test.py build /path/to/your/ios/project [scheme]

# Test Periphery setup
python cli_test.py setup /path/to/your/ios/project

# Scan with extra Periphery arguments
python cli_test.py scan /path/to/your/ios/project --verbose
```

This will show you exactly what each tool returns and help identify any issues with:
- Path resolution
- Periphery installation
- Project build issues
- Configuration problems

### Tool Timeouts and No Feedback

If you're experiencing timeouts when using the tools in Claude Desktop:

1. **Test from Command Line First**: Use `python cli_test.py scan /path/to/project` to verify the tool works outside of Claude Desktop

2. **Check Claude Desktop Logs**: Look for debug output in Claude Desktop's logs
   - Open Claude Desktop
   - Go to Help → Show Logs or check console output
   - Look for `[PERIPHERY-MCP DEBUG]` messages

3. **Test the Server Functions**: Use the included test script:
   ```bash
   python test_tools.py
   ```
   This tests the tool functions directly without MCP protocol overhead.

4. **Debug Steps**:
   - First, test with CLI: `python cli_test.py scan /your/project/path`
   - Check Claude Desktop logs for MCP communication errors
   - Verify your project path is correct and accessible
   - Ensure all prerequisites are installed

5. **Check Prerequisites**:
   - Verify Periphery is installed: `periphery version`
   - Ensure Xcode is installed and working
   - Test that your project builds in Xcode first
   - Make sure conda environment is properly activated

6. **Common Timeout Causes**:
   - Large projects take time to analyze (up to 30 minutes for very large codebases)
   - Network issues during Xcode dependency resolution
   - Missing build dependencies or certificates
   - Corrupted Xcode project files

### Debug Output

The server logs detailed debug information to stderr, which appears in Claude Desktop logs. Each tool execution shows:
- Input parameters and path resolution
- Command execution details and timing
- Error messages with full stack traces
- Periphery setup and scan progress

Example debug log entries:
```
[PERIPHERY-MCP DEBUG] periphery_scan called with project_path: /path/to/project, extra_args: None
[PERIPHERY-MCP DEBUG] Resolved project path: /path/to/project
[PERIPHERY-MCP DEBUG] Checking for config file: /path/to/project/.periphery.yml
[PERIPHERY-MCP DEBUG] Running build check
[PERIPHERY-MCP DEBUG] Running periphery scan: periphery scan --format json
[PERIPHERY-MCP DEBUG] Found 42 issues
```

### Testing with Your Project

To test with a real iOS/macOS project, modify the test script:
```python
# Add this to test_tools.py
result = project_build("/path/to/your/ios/project")
print(f"Real project test: {result}")
```
   - Look for `[PERIPHERY-MCP DEBUG]` messages

2. **Test the Server Manually**: Use the included test script:
   ```bash
   python test_mcp_server.py
   ```
   This will test basic server functionality and show debug output.

3. **Check Prerequisites**:
   - Verify Periphery is installed: `periphery version`
   - Ensure Xcode is installed and working
   - Test that your project builds in Xcode first

4. **Common Timeout Causes**:
   - Large projects take time to analyze (up to 30 minutes for very large codebases)
   - Network issues during Xcode dependency resolution
   - Missing build dependencies or certificates
   - Corrupted Xcode project files

### Debug Output

The server now logs detailed debug information to stderr, which appears in Claude Desktop logs. Each tool execution will show:
- Input parameters
- Path resolution
- Command execution details
- Error messages and stack traces
- Execution timing

### Common Issues

**"Project path does not exist"**
- Verify the path you're providing exists
- Use absolute paths when possible
- Check that you have read permissions for the directory

**"Periphery setup failed"**
- Ensure your project builds successfully in Xcode
- Check that all dependencies are properly configured
- Verify Periphery is installed: `periphery version`

**"Build failed"**
- Open project in Xcode and resolve any compilation errors
- Ensure all required certificates and provisioning profiles are available
- Check that the specified scheme exists

**Connection issues**
- Verify Claude Desktop configuration is correct
- Check that the server executable path is correct
- Ensure conda environment is activated
- Check Claude Desktop logs for error details

### Performance Tips

- For large projects, start with a subset using `extra_args: ["--verbose"]`
- Use build schemes that exclude test targets for faster analysis
- Consider excluding vendor/third-party code directories
- Run builds in Xcode first to ensure all dependencies are resolved

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