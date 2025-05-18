#!/bin/bash
# Startup script for Periphery MCP Server

# Activate conda environment and run the server
source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh
conda activate periphery-mcp
cd /Users/cculbreath/devlocal/codebase/periphery-mcp
python periphery-mcp-server.py
