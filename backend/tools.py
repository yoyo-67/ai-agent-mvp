"""MCP-style tools for file operations with workspace sandboxing."""

import json
import re
from pathlib import Path
from typing import Any

# Workspace root - all file operations are sandboxed here
WORKSPACE_ROOT = Path(__file__).parent.parent / "workspace"


# =============================================================================
# Path Security
# =============================================================================

def get_safe_path(path: str) -> Path:
    """
    Resolve path safely within workspace.
    Raises ValueError if path escapes workspace.
    """
    full_path = (WORKSPACE_ROOT / path).resolve()
    workspace_resolved = WORKSPACE_ROOT.resolve()

    if not str(full_path).startswith(str(workspace_resolved)):
        raise ValueError(f"Path '{path}' escapes workspace directory")

    return full_path


# =============================================================================
# Tool Implementations
# =============================================================================

def read_file(path: str) -> str:
    """Read the contents of a file."""
    try:
        safe_path = get_safe_path(path)
        if not safe_path.exists():
            return f"Error: File not found: {path}"
        if not safe_path.is_file():
            return f"Error: Not a file: {path}"
        return safe_path.read_text()
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates parent directories if needed."""
    try:
        safe_path = get_safe_path(path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(content)
        return f"Successfully wrote {len(content)} characters to {path}"
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error writing file: {e}"


def edit_file(path: str, search: str, replace: str) -> str:
    """Edit a file by replacing occurrences of search string with replace string."""
    try:
        safe_path = get_safe_path(path)
        if not safe_path.exists():
            return f"Error: File not found: {path}"

        content = safe_path.read_text()
        if search not in content:
            return f"Error: Search string not found in {path}"

        count = content.count(search)
        new_content = content.replace(search, replace)
        safe_path.write_text(new_content)

        return f"Replaced {count} occurrence(s) in {path}"
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error editing file: {e}"


def list_files(pattern: str = "*") -> str:
    """List files in workspace matching a glob pattern."""
    try:
        workspace_resolved = WORKSPACE_ROOT.resolve()
        matches = list(workspace_resolved.glob(pattern))

        # Get relative paths for files only
        relative_paths = [
            str(p.relative_to(workspace_resolved))
            for p in matches
            if p.is_file()
        ]

        if not relative_paths:
            return "No files found matching pattern"

        return "\n".join(sorted(relative_paths))
    except Exception as e:
        return f"Error listing files: {e}"


def search_files(pattern: str, file_pattern: str = "**/*") -> str:
    """Search for a regex pattern in files matching file_pattern."""
    try:
        regex = re.compile(pattern)
        results = []
        workspace_resolved = WORKSPACE_ROOT.resolve()

        for file_path in workspace_resolved.glob(file_pattern):
            if not file_path.is_file():
                continue
            try:
                content = file_path.read_text()
                for i, line in enumerate(content.split("\n"), 1):
                    if regex.search(line):
                        rel_path = file_path.relative_to(workspace_resolved)
                        results.append(f"{rel_path}:{i}: {line.strip()}")
            except Exception:
                # Skip files that can't be read (binary, etc.)
                pass

        if not results:
            return "No matches found"

        return "\n".join(results)
    except re.error as e:
        return f"Error: Invalid regex pattern: {e}"
    except Exception as e:
        return f"Error searching files: {e}"


# =============================================================================
# Tool Registry
# =============================================================================

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_files": list_files,
    "search_files": search_files,
}

# OpenAI function calling format
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file at the specified path within the workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file (e.g., 'sample.txt' or 'data/config.json')"
                    }
                },
                "required": ["path"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within the workspace"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by replacing all occurrences of a search string with a replacement string",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within the workspace"
                    },
                    "search": {
                        "type": "string",
                        "description": "The string to search for in the file"
                    },
                    "replace": {
                        "type": "string",
                        "description": "The string to replace the search string with"
                    }
                },
                "required": ["path", "search", "replace"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in the workspace matching a glob pattern",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match files (e.g., '*.txt', '**/*.py'). Defaults to '*'",
                        "default": "*"
                    }
                },
                "required": [],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for a regex pattern in files within the workspace (grep-like)",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regular expression pattern to search for"
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "Glob pattern to filter which files to search (e.g., '*.py'). Defaults to '**/*'",
                        "default": "**/*"
                    }
                },
                "required": ["pattern"],
                "additionalProperties": False
            }
        }
    }
]


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool by name with given arguments."""
    if name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool: {name}"

    try:
        return TOOL_FUNCTIONS[name](**arguments)
    except TypeError as e:
        return f"Error: Invalid arguments for {name}: {e}"
    except Exception as e:
        return f"Error executing {name}: {e}"
