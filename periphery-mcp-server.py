#!/usr/bin/env python
"""
periphery_mcp_server.py
-----------------------
MCP server that wraps Periphery for static-analysis + interactive setup.

▶  Requirements
    conda activate periphery-mcp
    pip install 'mcp[cli]==1.*' fastapi uvicorn pexpect rich

▶  Run
    python periphery-mcp-server.py  # runs as stdio MCP server
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import pexpect
from mcp.server.fastmcp import FastMCP


# Helper function for debugging - logs to stderr so it appears in Claude Desktop logs
def debug_log(message: str):
    print(f"[PERIPHERY-MCP DEBUG] {message}", file=sys.stderr, flush=True)


# Initialize the FastMCP server
mcp = FastMCP(
    name="periphery-mcp",
    description="Exposes Periphery static-analysis functions to Model Context Protocol clients"
)

debug_log("FastMCP server initialized")


# ────────────────────────────────────────────────────────────────────────────────
#  Tool 1 – Periphery interactive setup
# ────────────────────────────────────────────────────────────────────────────────
    def _parse_schemes_from_output(self, output: str) -> List[str]:
        """Parse scheme names from xcodebuild -list output."""
        schemes = []
        in_schemes_section = False
        
        for line in output.split('\n'):
            line = line.strip()
            if 'Schemes:' in line:
                in_schemes_section = True
                continue
            elif in_schemes_section:
                if line and not line.startswith('Build Configurations:') and not line.startswith('Targets:'):
                    if line != 'Schemes:':
                        schemes.append(line)
                else:
                    break
        
        return schemes
    
    def _setup_spm_project(self, proj: Path) -> Dict[str, Any]:
        """Setup configuration for Swift Package Manager projects."""
        debug_log("Setting up SPM project")
        
        # For SPM projects, we don't need a complex config
        config_content = """format: xcode
"""
        
        config_file = proj / ".periphery.yml"
        try:
            config_file.write_text(config_content)
            debug_log("Created basic SPM configuration")
            
            # Test with a quick SPM scan
            test_cmd = ["periphery", "scan", "--quiet", "--format", "json"]
            test_result = subprocess.run(
                test_cmd,
                cwd=proj,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if test_result.returncode == 0:
                debug_log("SPM configuration validated successfully")
                return {
                    "success": True,
                    "yml": config_content,
                    "log_tail": [
                        "Swift Package Manager project detected",
                        "Created basic configuration",
                        "Configuration validated successfully"
                    ]
                }
            else:
                debug_log(f"SPM configuration test failed: {test_result.stderr}")
                return {
                    "success": False,
                    "yml": None,
                    "log_tail": [
                        "Swift Package Manager project detected",
                        f"Error: {test_result.stderr.splitlines()[-1] if test_result.stderr else 'Unknown error'}"
                    ]
                }
        except Exception as e:
            debug_log(f"Failed to setup SPM project: {e}")
            return {
                "success": False,
                "yml": None,
                "log_tail": [f"Error setting up SPM project: {str(e)}"]
            }


    """Run Periphery's guided setup when no .periphery.yml exists."""
    debug_log(f"periphery_setup called with project_path: {project_path}")
    
    try:
        # More robust path resolution - preserve case and handle Path conversion carefully
        proj = Path(project_path).expanduser()
        if not proj.is_absolute():
            proj = proj.resolve()
        debug_log(f"Resolved project path: {proj}")
        debug_log(f"Project path exists: {proj.exists()}")
        
        if not proj.exists():
            debug_log(f"Project path does not exist: {proj}")
            return {
                "success": False,
                "yml": None,
                "log_tail": [f"Error: Project path does not exist: {proj}"]
            }

        # Check if .periphery.yml already exists
        config_file = proj / ".periphery.yml"
        if config_file.exists():
            debug_log("Config file already exists")
            return {
                "success": True,
                "yml": config_file.read_text(),
                "log_tail": ["Configuration file already exists"]
            }

        # Find the project file (.xcodeproj or .xcworkspace)
        xcodeproj_files = list(proj.glob("*.xcodeproj"))
        xcworkspace_files = list(proj.glob("*.xcworkspace"))
        
        project_file = None
        if xcworkspace_files:
            # Prefer workspace over project if both exist
            project_file = xcworkspace_files[0]
            debug_log(f"Found workspace: {project_file.name}")
        elif xcodeproj_files:
            project_file = xcodeproj_files[0]
            debug_log(f"Found project: {project_file.name}")
        else:
            # Check for SPM projects
            package_swift = proj / "Package.swift"
            if package_swift.exists():
                debug_log("Found Package.swift - SPM project")
                return _setup_spm_project(proj)._setup_spm_project(proj)
            else:
                debug_log("No .xcodeproj, .xcworkspace, or Package.swift found")
                return {
                    "success": False,
                    "yml": None,
                    "log_tail": ["Error: No Xcode project, workspace, or Package.swift found in directory"]
                }
        
        project_name = project_file.name
        
        # For workspaces and complex projects, we need to discover schemes
        # Let's try to list available schemes first
        debug_log("Discovering available schemes...")
        list_schemes_cmd = ["xcodebuild", "-list"]
        if project_file.suffix == ".xcworkspace":
            list_schemes_cmd.extend(["-workspace", str(project_file)])
        else:
            list_schemes_cmd.extend(["-project", str(project_file)])
        
        try:
            schemes_result = subprocess.run(
                list_schemes_cmd,
                cwd=proj,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if schemes_result.returncode == 0:
                schemes = _parse_schemes_from_output(schemes_result.stdout)
                debug_log(f"Available schemes: {schemes}")
                
                if not schemes:
                    scheme_name = project_file.stem  # Fallback to project name
                    debug_log(f"No schemes found, using fallback: {scheme_name}")
                else:
                    # Use the first scheme, or prefer one that matches the project name
                    scheme_name = schemes[0]
                    for scheme in schemes:
                        if scheme.lower() == project_file.stem.lower():
                            scheme_name = scheme
                            break
                    debug_log(f"Selected scheme: {scheme_name}")
            else:
                debug_log(f"Failed to list schemes: {schemes_result.stderr}")
                scheme_name = project_file.stem  # Fallback
        except subprocess.TimeoutExpired:
            debug_log("Scheme discovery timed out, using fallback")
            scheme_name = project_file.stem
        
        debug_log(f"Found project: {project_name}, scheme: {scheme_name}")

        # Run periphery scan with explicit parameters to generate and test configuration
        debug_log("Running Periphery scan with explicit parameters")
        scan_cmd = ["periphery", "scan", "--format", "json", "--quiet"]
        
        # Add project/workspace parameter
        if project_file.suffix == ".xcworkspace":
            scan_cmd.extend(["--workspace", str(project_file)])
        else:
            scan_cmd.extend(["--project", str(project_file)])
        
        scan_cmd.extend(["--schemes", scheme_name])
        
        debug_log(f"Running command: {' '.join(scan_cmd)}")
        scan_result = subprocess.run(
            scan_cmd,
            cwd=proj,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if scan_result.returncode == 0:
            debug_log("Scan completed successfully")
            
            # Create a .periphery.yml configuration file for future use
            if project_file.suffix == ".xcworkspace":
                config_content = f"""workspace: {project_name}
schemes:
  - {scheme_name}
format: xcode
"""
            else:
                config_content = f"""project: {project_name}
schemes:
  - {scheme_name}
format: xcode
"""
            try:
                config_file.write_text(config_content)
                debug_log(f"Config file written to {config_file}")
            except Exception as e:
                debug_log(f"Warning: Could not write config file: {e}")
            
            # Parse the JSON output to get unused code items
            try:
                scan_data = json.loads(scan_result.stdout)
                unused_count = len(scan_data) if isinstance(scan_data, list) else 0
                debug_log(f"Found {unused_count} unused code items")
                
                log_tail = [
                    f"Successfully scanned project: {project_name}",
                    f"Scheme: {scheme_name}",
                    f"Found {unused_count} unused code items",
                    "Configuration saved to .periphery.yml"
                ]
                
                # Add some sample results to log
                if unused_count > 0:
                    sample_items = scan_data[:3] if isinstance(scan_data, list) else []
                    for item in sample_items:
                        if isinstance(item, dict) and 'name' in item and 'location' in item:
                            location = item['location'].split('/')[-1] if '/' in item['location'] else item['location']
                            log_tail.append(f"  - {item['name']} in {location}")
                    if unused_count > 3:
                        log_tail.append(f"  ... and {unused_count - 3} more items")
                
                return {
                    "success": True,
                    "yml": config_content,
                    "log_tail": log_tail
                }
                
            except json.JSONDecodeError as e:
                debug_log(f"Could not parse scan results as JSON: {e}")
                # Still consider it successful since the scan ran
                return {
                    "success": True,
                    "yml": config_content,
                    "log_tail": [
                        f"Successfully scanned project: {project_name}",
                        f"Scheme: {scheme_name}",
                        "Configuration saved to .periphery.yml",
                        "Warning: Could not parse scan results"
                    ]
                }
        else:
            debug_log(f"Scan failed with exit code {scan_result.returncode}")
            debug_log(f"Scan stderr: {scan_result.stderr}")
            
            # Extract meaningful error message
            error_lines = scan_result.stderr.strip().split('\n')
            error_msg = error_lines[-1] if error_lines else "Unknown error"
            
            return {
                "success": False,
                "yml": None,
                "log_tail": [
                    f"Failed to scan project: {project_name}",
                    f"Scheme: {scheme_name}",
                    f"Error: {error_msg}",
                    "Try running 'xcodebuild clean' and ensure the project builds successfully"
                ]
            }
            
    except subprocess.TimeoutExpired:
        debug_log("Scan timed out after 10 minutes")
        return {
            "success": False,
            "yml": None,
            "log_tail": ["Error: Scan timed out after 10 minutes"]
        }
    except Exception as e:
        debug_log(f"Error in periphery_setup: {e}")
        debug_log(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "yml": None,
            "log_tail": [f"Error: {str(e)}"]
        } First check for scheme selection
            if "delimit choices" in prompt_lower and "1 physcloudresume" in prompt_lower:
                debug_log("Detected scheme selection")
                return "1"
            
            # Check for specific question patterns
            if "objective-c" in prompt_lower and ("(y)es/(n)o" in prompt_lower or "code" in prompt_lower):
                debug_log("Detected Objective-C question")
                return "n"
            elif "public" in prompt_lower and "declarations" in prompt_lower and "use" in prompt_lower:
                debug_log("Detected public declarations question") 
                return "n"
            elif "save configuration" in prompt_lower and ".periphery.yml" in prompt_lower:
                debug_log("Detected save configuration question")
                return "y"
            elif "configuration" in prompt_lower and ".periphery.yml" in prompt_lower:
                debug_log("Detected save configuration question (variant)")
                return "y"
            
            # More general patterns
            elif "(y)es/(n)o" in prompt_lower:
                if "save" in prompt_lower or ".yml" in prompt_lower:
                    debug_log("General save question")
                    return "y"
                else:
                    debug_log("General yes/no question, defaulting to no")
                    return "n"
            elif "delimit choices" in prompt_lower or "select" in prompt_lower:
                debug_log("Selection question, choosing 1")
                return "1"
            else:
                debug_log(f"Unknown prompt pattern: '{prompt}'")
                return "1"

        result = run_interactive_setup(proj, prompt_callback)
        debug_log(f"Setup result: {result}")
        
        return {
            "success": result["success"],
            "yml": result["yml"],
            "log_tail": result["log_tail"]
        }
    except Exception as e:
        debug_log(f"Error in periphery_setup: {e}")
        debug_log(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "yml": None,
            "log_tail": [f"Error: {str(e)}"]
        }


# ────────────────────────────────────────────────────────────────────────────────
#  Tool 2 – project build checker
# ────────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def project_build(project_path: str, scheme: Optional[str] = None) -> Dict[str, Any]:
    """Try to build the project (xcodebuild) and return result."""
    debug_log(f"project_build called with project_path: {project_path}, scheme: {scheme}")
    
    try:
        # More robust path resolution - preserve case and handle Path conversion carefully
        proj = Path(project_path).expanduser()
        if not proj.is_absolute():
            proj = proj.resolve()
        debug_log(f"Resolved project path: {proj}")
        debug_log(f"Project path exists: {proj.exists()}")
        
        if not proj.exists():
            debug_log(f"Project path does not exist: {proj}")
            return {
                "build_ok": False,
                "log_tail": [f"Error: Project path does not exist: {proj}"]
            }
        
        # Find the .xcodeproj file
        xcodeproj_files = list(proj.glob("*.xcodeproj"))
        if not xcodeproj_files:
            debug_log("No .xcodeproj file found in project directory")
            return {
                "build_ok": False,
                "log_tail": ["Error: No .xcodeproj file found in project directory"]
            }
        
        xcodeproj_path = xcodeproj_files[0]
        debug_log(f"Found Xcode project: {xcodeproj_path}")
        
        # If no scheme provided, try to detect it from the project name
        if not scheme:
            scheme = xcodeproj_path.stem  # Get filename without .xcodeproj extension
            debug_log(f"Using inferred scheme: {scheme}")
        
        # Use similar build arguments to what Periphery uses for better compatibility
        args = [
            "xcodebuild",
            "-project", str(xcodeproj_path),
            "-scheme", scheme,
            "-quiet",
            "build-for-testing",
            "CODE_SIGNING_ALLOWED=NO",
            "ENABLE_BITCODE=NO", 
            "DEBUG_INFORMATION_FORMAT=dwarf",
            "COMPILER_INDEX_STORE_ENABLE=YES",
            "INDEX_ENABLE_DATA_STORE=YES"
        ]
        
        debug_log(f"Running command: {' '.join(args)}")
        debug_log(f"Working directory: {proj}")

        subprocess.run(
            args,
            cwd=proj,
            capture_output=True,
            text=True,
            check=True,
            timeout=900,
        )
        debug_log("Build successful")
        return {"build_ok": True, "log_tail": []}
    except subprocess.CalledProcessError as e:
        debug_log(f"Build failed with exit code {e.returncode}")
        debug_log(f"Build stderr: {e.stderr}")
        return {
            "build_ok": False,
            "log_tail": e.stderr.splitlines()[-200:],
        }
    except subprocess.TimeoutExpired:
        debug_log("Build timed out after 900 seconds")
        return {
            "build_ok": False,
            "log_tail": ["Error: Build timed out after 15 minutes"]
        }
    except Exception as e:
        debug_log(f"Error in project_build: {e}")
        debug_log(f"Traceback: {traceback.format_exc()}")
        return {
            "build_ok": False,
            "log_tail": [f"Error: {str(e)}"]
        }


# ────────────────────────────────────────────────────────────────────────────────
#  Tool 3 – Periphery scan with all the bells & whistles
# ────────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def periphery_scan(
    project_path: str,
    extra_args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run Periphery scan; auto-setup and structured error handling."""
    debug_log(f"periphery_scan called with project_path: {project_path}, extra_args: {extra_args}")
    
    try:
        # More robust path resolution - preserve case and handle Path conversion carefully  
        proj = Path(project_path).expanduser()
        if not proj.is_absolute():
            proj = proj.resolve()
        debug_log(f"Resolved project path: {proj}")
        debug_log(f"Project path exists: {proj.exists()}")
        
        if not proj.exists():
            debug_log(f"Project path does not exist: {proj}")
            return {
                "build_ok": False,
                "issues": [],
                "raw_json": None,
                "build_error": {
                    "summary": f"Project path does not exist: {proj}",
                    "log_tail": [],
                    "exit_code": -1,
                },
            }

        # ── 1. Check if .periphery.yml exists, run setup if needed ─────────
        cfg_file = proj / ".periphery.yml"
        debug_log(f"Checking for config file: {cfg_file}")
        
        if not cfg_file.exists():
            debug_log("Config file doesn't exist, running setup (which includes building)")
            setup_res = periphery_setup(str(proj))
            if not setup_res["success"]:
                debug_log(f"Setup failed: {setup_res}")
                return {
                    "build_ok": False,
                    "issues": [],
                    "raw_json": None,
                    "build_error": {
                        "summary": "Periphery setup failed - this usually means the project doesn't build",
                        "log_tail": setup_res["log_tail"],
                        "exit_code": -1,
                    },
                }
            # Note: We don't write the YAML config since user chose not to save during setup
            # but that's fine - Periphery will run with the command line args it discovered
        else:
            debug_log("Found existing .periphery.yml config file")

        # ── 2. Run Periphery scan ──────────────────────────────────────────
        args = ["periphery", "scan", "--format", "json"]
        if extra_args:
            args += extra_args
        
        debug_log(f"Running periphery scan: {' '.join(args)}")
        debug_log(f"Working directory: {proj}")

        cp = subprocess.run(
            args,
            cwd=proj,
            capture_output=True,
            text=True,
            check=True,
            timeout=1800,
        )
        
        debug_log("Periphery scan completed successfully")
        debug_log(f"Stdout length: {len(cp.stdout)} chars")
        
        data = json.loads(cp.stdout)
        debug_log(f"Parsed JSON structure: {type(data)}")
        
        # Let's inspect the first few characters of the JSON to understand structure
        debug_log(f"First 200 chars of JSON: {cp.stdout[:200]}")
        
        # Handle different JSON structures that Periphery might return
        if isinstance(data, list):
            # If data is a list, assume it's directly the list of results
            results = data
            debug_log(f"Processing as list with {len(results)} items")
            if results:
                debug_log(f"First result sample: {results[0]}")
        elif isinstance(data, dict) and "results" in data:
            # If data is a dict with "results" key
            results = data["results"]
        else:
            # If data is a dict without "results", assume it's the results themselves
            results = [data] if isinstance(data, dict) else []
        
        debug_log(f"Found {len(results)} results")
        
        issues = []
        for i, r in enumerate(results):
            debug_log(f"Processing result {i}: {type(r)}")
            if isinstance(r, dict) and all(key in r for key in ["kind", "name", "location"]):
                # Parse location string like: "/path/to/file.swift:39:18"
                location_str = r["location"]
                if ":" in location_str:
                    # Split location into file and line number
                    location_parts = location_str.rsplit(":", 2)
                    file_path = location_parts[0]
                    line_number = int(location_parts[1]) if len(location_parts) > 1 else 1
                else:
                    file_path = location_str
                    line_number = 1
                
                issues.append({
                    "kind": r["kind"],
                    "identifier": r["name"],
                    "file": file_path,
                    "line": line_number,
                })
            else:
                missing_keys = [key for key in ["kind", "name", "location"] if key not in r]
                debug_log(f"Skipping result {i}, missing keys: {missing_keys}")
        
        debug_log(f"Processed {len(issues)} valid issues")
        
        return {
            "build_ok": True,
            "issues": issues,
            "raw_json": data,
            "build_error": None,
        }
    except subprocess.CalledProcessError as e:
        debug_log(f"Periphery scan failed with exit code {e.returncode}")
        debug_log(f"Stderr: {e.stderr}")
        summary = next(
            (l for l in e.stderr.splitlines() if l.strip()), "scan failed"
        )
        return {
            "build_ok": False,
            "issues": [],
            "raw_json": None,
            "build_error": {
                "summary": summary[:250],
                "log_tail": e.stderr.splitlines()[-200:],
                "exit_code": e.returncode,
            },
        }
    except subprocess.TimeoutExpired:
        debug_log("Periphery scan timed out after 1800 seconds")
        return {
            "build_ok": False,
            "issues": [],
            "raw_json": None,
            "build_error": {
                "summary": "Scan timed out after 30 minutes",
                "log_tail": ["Error: Periphery scan timed out"],
                "exit_code": -1,
            },
        }
    except json.JSONDecodeError as e:
        debug_log(f"Failed to parse Periphery JSON output: {e}")
        return {
            "build_ok": False,
            "issues": [],
            "raw_json": None,
            "build_error": {
                "summary": "Failed to parse Periphery output",
                "log_tail": [f"JSON decode error: {str(e)}"],
                "exit_code": -1,
            },
        }
    except Exception as e:
        debug_log(f"Error in periphery_scan: {e}")
        debug_log(f"Traceback: {traceback.format_exc()}")
        return {
            "build_ok": False,
            "issues": [],
            "raw_json": None,
            "build_error": {
                "summary": f"Unexpected error: {str(e)}",
                "log_tail": [str(e)],
                "exit_code": -1,
            },
        }


# ────────────────────────────────────────────────────────────────────────────────
#  Launch the MCP server
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    debug_log("Starting Periphery MCP server...")
    try:
        # Run the MCP server using stdio transport (required for Claude Desktop)
        mcp.run()
    except Exception as e:
        debug_log(f"Error starting server: {e}")
        debug_log(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
