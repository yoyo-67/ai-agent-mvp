# Backend - Tools

Tools give the LLM the ability to **take actions**. Without tools, it can only generate text.

## Tool Definition Format

OpenAI expects tools in this JSON schema format:

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to read"
                    }
                },
                "required": ["path"]
            }
        }
    },
    # ... more tools
]
```

**Key parts:**
- `name` - The function name the LLM will call
- `description` - Helps the LLM understand when to use it
- `parameters` - JSON Schema defining the arguments

## Our 5 Tools

### 1. read_file
```python
{
    "name": "read_file",
    "description": "Read the contents of a file",
    "parameters": {
        "properties": {
            "path": {"type": "string", "description": "Path to the file"}
        },
        "required": ["path"]
    }
}
```

### 2. write_file
```python
{
    "name": "write_file",
    "description": "Write content to a file (creates or overwrites)",
    "parameters": {
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"}
        },
        "required": ["path", "content"]
    }
}
```

### 3. edit_file
```python
{
    "name": "edit_file",
    "description": "Edit a file by replacing a search string",
    "parameters": {
        "properties": {
            "path": {"type": "string"},
            "search": {"type": "string", "description": "Text to find"},
            "replace": {"type": "string", "description": "Replacement text"}
        },
        "required": ["path", "search", "replace"]
    }
}
```

### 4. list_files
```python
{
    "name": "list_files",
    "description": "List files matching a glob pattern",
    "parameters": {
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern (default: *)"
            }
        },
        "required": []
    }
}
```

### 5. search_files
```python
{
    "name": "search_files",
    "description": "Search for a pattern in files (like grep)",
    "parameters": {
        "properties": {
            "pattern": {"type": "string", "description": "Regex to search"},
            "file_pattern": {"type": "string", "description": "Files to search"}
        },
        "required": ["pattern"]
    }
}
```

## Tool Implementation

### Workspace Sandboxing

All file operations are **sandboxed** to the `workspace/` folder:

```python
WORKSPACE_DIR = Path(__file__).parent.parent / "workspace"

def get_safe_path(path: str) -> Path | None:
    """Resolve path safely within workspace."""
    try:
        # Resolve the full path
        full_path = (WORKSPACE_DIR / path).resolve()

        # Check it's still inside workspace (prevents ../ attacks)
        if WORKSPACE_DIR.resolve() in full_path.parents or full_path == WORKSPACE_DIR.resolve():
            return full_path

        # Also allow if it's directly in workspace
        if full_path.parent == WORKSPACE_DIR.resolve():
            return full_path

        return None
    except Exception:
        return None
```

**Security:** This prevents path traversal attacks like `../../etc/passwd`.

### Tool Functions

```python
def read_file(path: str) -> str:
    """Read file contents."""
    safe_path = get_safe_path(path)
    if not safe_path:
        return f"Error: Invalid path '{path}'"

    if not safe_path.exists():
        return f"Error: File not found '{path}'"

    return safe_path.read_text()


def write_file(path: str, content: str) -> str:
    """Write content to file."""
    safe_path = get_safe_path(path)
    if not safe_path:
        return f"Error: Invalid path '{path}'"

    # Create parent directories if needed
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(content)

    return f"Successfully wrote to '{path}'"


def edit_file(path: str, search: str, replace: str) -> str:
    """Replace text in file."""
    safe_path = get_safe_path(path)
    if not safe_path or not safe_path.exists():
        return f"Error: File not found '{path}'"

    content = safe_path.read_text()

    if search not in content:
        return f"Error: Search string not found in '{path}'"

    new_content = content.replace(search, replace, 1)  # Replace first occurrence
    safe_path.write_text(new_content)

    return f"Successfully edited '{path}'"


def list_files(pattern: str = "*") -> str:
    """List files matching pattern."""
    matches = list(WORKSPACE_DIR.glob(pattern))

    if not matches:
        return "No files found"

    # Return relative paths
    return "\n".join(
        str(p.relative_to(WORKSPACE_DIR))
        for p in sorted(matches)
        if p.is_file()
    )


def search_files(pattern: str, file_pattern: str = "*") -> str:
    """Search for pattern in files."""
    import re

    results = []
    for file_path in WORKSPACE_DIR.glob(file_pattern):
        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(pattern, line):
                    rel_path = file_path.relative_to(WORKSPACE_DIR)
                    results.append(f"{rel_path}:{i}: {line}")
        except Exception:
            continue

    return "\n".join(results) if results else "No matches found"
```

## Tool Dispatcher

Maps tool names to functions:

```python
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_files": list_files,
    "search_files": search_files,
}


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool by name with arguments."""
    if name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool '{name}'"

    try:
        return TOOL_FUNCTIONS[name](**arguments)
    except Exception as e:
        return f"Error: {e}"
```

## How the LLM Uses Tools

1. LLM sees the tool definitions in the API call
2. Based on user request, it decides to call a tool
3. It generates a tool_call with name and JSON arguments
4. Backend executes the tool
5. Result is added to messages as a "tool" role message
6. LLM sees the result and can respond or call more tools

### Example Conversation

```
User: "What's in sample.txt?"

LLM thinks: "I need to read the file"
LLM outputs: tool_call(name="read_file", arguments={"path": "sample.txt"})

Backend executes: read_file("sample.txt")
Result: "Hello! This is a sample..."

Messages now include:
- user: "What's in sample.txt?"
- assistant: [tool_call: read_file]
- tool: "Hello! This is a sample..."

LLM sees result and responds:
"The file sample.txt contains a greeting and some test data..."
```

## Error Handling

Tools return error strings (not exceptions) so the LLM can understand and retry:

```python
def read_file(path: str) -> str:
    safe_path = get_safe_path(path)
    if not safe_path:
        return f"Error: Invalid path '{path}'"  # LLM sees this

    if not safe_path.exists():
        return f"Error: File not found '{path}'"  # LLM can try different path
```

The agent loop checks for errors:

```python
is_error = result.startswith("Error:")
```

## Next

[05-frontend-streaming.md](./05-frontend-streaming.md) - SSE client and React state
