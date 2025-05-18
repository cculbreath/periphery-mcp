#!/usr/bin/env python
"""
periphery_mcp_server.py
-----------------------
MCP server that wraps Periphery for static-analysis + interactive setup.

▶  Requirements
    conda activate periphery-mcp
    pip install 'mcp[cli]==1.*' fastapi uvicorn pexpect rich

▶  Run
    python periphery_mcp_server.py  # listens on http://localhost:4000
"""
from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

import pexpect
from mcp.server.fastmcp import FastMCP

# ────────────────────────────────────────────────────────────────────────────────
#  Helper ─ run periphery interactively (setup) through a pseudo-terminal
# ────────────────────────────────────────────────────────────────────────────────
def run_interactive_setup(project_path: Path, prompt_callback) -> Dict[str, Any]:
    """
    Launch `periphery scan --setup` inside `project_path` and proxy each prompt
    through `prompt_callback(prompt:str) -> str`.
    Returns a dict with keys {success, yml, log_tail}.
    """
    child = pexpect.spawn(
        "periphery scan --setup",
        cwd=str(project_path),
        encoding="utf-8",
        echo=False,
    )
    log: List[str] = []
    yml_lines: List[str] = []
    success = False

    try:
        while True:
            idx = child.expect(
                [r"\r\n", r"\n", pexpect.EOF, pexpect.TIMEOUT], timeout=10
            )

            if idx in (0, 1):  # got a line
                line = child.before.strip()
                if line:
                    log.append(line)

                    # collect YAML once it starts (Periphery prints "---" first)
                    if line.startswith("---") or yml_lines:
                        yml_lines.append(line)

                    # treat terminal ':' or '?' as a prompt
                    if line.endswith((":", "?")):
                        answer = prompt_callback(line)
                        child.sendline(answer)

            elif idx == 2:  # EOF
                success = child.exitstatus == 0 and bool(yml_lines)
                break
            # idx==3 is TIMEOUT; just loop again
    finally:
        try:
            child.close()
        except Exception:
            pass

    return {
        "success": success,
        "yml": "\n".join(yml_lines) if success else None,
        "log_tail": log[-200:],
    }


# Initialize the FastMCP server
mcp = FastMCP(
    name="periphery-mcp",
    description="Exposes Periphery static-analysis functions to Model Context Protocol clients"
)


# ────────────────────────────────────────────────────────────────────────────────
#  Tool 1 – Periphery interactive setup
# ────────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def periphery_setup(project_path: str) -> Dict[str, Any]:
    """Run Periphery's guided setup when no .periphery.yml exists."""
    proj = Path(project_path).expanduser().resolve()

    # Simple prompt callback that returns default answers
    # In a real interactive scenario, this would need to handle streaming
    def prompt_callback(prompt: str) -> str:
        # Provide some reasonable defaults for common prompts
        if "scheme" in prompt.lower():
            return ""  # Use default scheme
        elif "target" in prompt.lower():
            return ""  # Use default target
        elif "configuration" in prompt.lower():
            return "Debug"
        else:
            return ""  # Default to empty/default answer

    result = run_interactive_setup(proj, prompt_callback)
    return {
        "success": result["success"],
        "yml": result["yml"],
        "log_tail": result["log_tail"]
    }


# ────────────────────────────────────────────────────────────────────────────────
#  Tool 2 – project build checker
# ────────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def project_build(project_path: str, scheme: Optional[str] = None) -> Dict[str, Any]:
    """Try to build the project (xcodebuild) and return result."""
    proj = Path(project_path).expanduser().resolve()
    args = ["xcodebuild", "build", "-quiet"]
    if scheme:
        args += ["-scheme", scheme]

    try:
        subprocess.run(
            args,
            cwd=proj,
            capture_output=True,
            text=True,
            check=True,
            timeout=900,
        )
        return {"build_ok": True, "log_tail": []}
    except subprocess.CalledProcessError as e:
        return {
            "build_ok": False,
            "log_tail": e.stderr.splitlines()[-200:],
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
    proj = Path(project_path).expanduser().resolve()

    # ── 1. Ensure .periphery.yml exists ─────────────────────────────────
    cfg_file = proj / ".periphery.yml"
    if not cfg_file.exists():
        setup_res = periphery_setup(str(proj))
        if not setup_res["success"]:
            return {
                "build_ok": False,
                "issues": [],
                "raw_json": None,
                "build_error": {
                    "summary": "Periphery setup failed",
                    "log_tail": setup_res["log_tail"],
                    "exit_code": -1,
                },
            }
        cfg_file.write_text(setup_res["yml"])

    # ── 2. Build check first (optional but fast) ───────────────────────
    build_res = project_build(str(proj))
    if not build_res["build_ok"]:
        return {
            "build_ok": False,
            "issues": [],
            "raw_json": None,
            "build_error": {
                "summary": "Build failed – see log_tail",
                "log_tail": build_res["log_tail"],
                "exit_code": 1,
            },
        }

    # ── 3. Run Periphery scan ──────────────────────────────────────────
    args = ["periphery", "scan", "--format", "json"]
    if extra_args:
        args += extra_args

    try:
        cp = subprocess.run(
            args,
            cwd=proj,
            capture_output=True,
            text=True,
            check=True,
            timeout=1800,
        )
        data = json.loads(cp.stdout)
        issues = [
            {
                "kind": r["kind"],
                "identifier": r["name"],
                "file": r["location"]["file"],
                "line": r["location"]["line"],
            }
            for r in data["results"]
        ]
        return {
            "build_ok": True,
            "issues": issues,
            "raw_json": data,
            "build_error": None,
        }
    except subprocess.CalledProcessError as e:
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


# ────────────────────────────────────────────────────────────────────────────────
#  Launch the MCP server
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    # Use the streamable HTTP app with custom host and port
    uvicorn.run(mcp.streamable_http_app, host="0.0.0.0", port=4000)
