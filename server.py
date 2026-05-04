# server.py

import json
import os
from datetime import datetime
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
import logging
logging.basicConfig(level=logging.DEBUG)
from mcp import types

# ── Data Storage Setup ────────────────────────────────────────────────────────
DATA_DIR   = Path(__file__).parent / "data"
NOTES_FILE = DATA_DIR / "notes.json"
TODOS_FILE = DATA_DIR / "todos.json"

# Create data directory if it doesn't exist
DATA_DIR.mkdir(exist_ok=True)


# ── Helper: Load/Save JSON ────────────────────────────────────────────────────
def load_json(filepath: Path) -> list:
    """Load data from JSON file. Returns empty list if file doesn't exist."""
    if not filepath.exists():
        return []
    with open(filepath, "r") as f:
        return json.load(f)


def save_json(filepath: Path, data: list):
    """Save data to JSON file."""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def get_timestamp() -> str:
    """Returns current timestamp as string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Initialize MCP Server ─────────────────────────────────────────────────────
server = Server("notes-todo-mcp")


# ── Register All Tools ────────────────────────────────────────────────────────
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Register all available tools with the MCP server."""
    return [

        # ── Notes Tools ───────────────────────────────────────────────────────
        types.Tool(
            name="add_note",
            description="Add a new note with a title and content",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the note"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content/body of the note"
                    },
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated tags e.g. 'work,important'"
                    }
                },
                "required": ["title", "content"]
            }
        ),

        types.Tool(
            name="list_notes",
            description="List all saved notes with their titles and IDs",
            inputSchema={
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "Optional: filter notes by tag"
                    }
                }
            }
        ),

        types.Tool(
            name="read_note",
            description="Read the full content of a specific note by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to read"
                    }
                },
                "required": ["note_id"]
            }
        ),

        types.Tool(
            name="update_note",
            description="Update the title or content of an existing note",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to update"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title (optional)"
                    },
                    "content": {
                        "type": "string",
                        "description": "New content (optional)"
                    }
                },
                "required": ["note_id"]
            }
        ),

        types.Tool(
            name="delete_note",
            description="Delete a note by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to delete"
                    }
                },
                "required": ["note_id"]
            }
        ),

        types.Tool(
            name="search_notes",
            description="Search notes by keyword in title or content",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Keyword to search for"
                    }
                },
                "required": ["keyword"]
            }
        ),

        # ── Todo Tools ────────────────────────────────────────────────────────
        types.Tool(
            name="add_todo",
            description="Add a new todo task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The todo task description"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority level: low, medium, high",
                        "enum": ["low", "medium", "high"]
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date in YYYY-MM-DD format (optional)"
                    }
                },
                "required": ["task"]
            }
        ),

        types.Tool(
            name="list_todos",
            description="List all todo tasks, optionally filtered by status or priority",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status: pending or completed",
                        "enum": ["pending", "completed", "all"]
                    },
                    "priority": {
                        "type": "string",
                        "description": "Filter by priority: low, medium, high",
                        "enum": ["low", "medium", "high"]
                    }
                }
            }
        ),

        types.Tool(
            name="complete_todo",
            description="Mark a todo task as completed",
            inputSchema={
                "type": "object",
                "properties": {
                    "todo_id": {
                        "type": "string",
                        "description": "The ID of the todo to mark as completed"
                    }
                },
                "required": ["todo_id"]
            }
        ),

        types.Tool(
            name="delete_todo",
            description="Delete a todo task by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "todo_id": {
                        "type": "string",
                        "description": "The ID of the todo to delete"
                    }
                },
                "required": ["todo_id"]
            }
        ),

        types.Tool(
            name="get_summary",
            description="Get a summary of all notes and todos — counts, priorities, pending tasks",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


# ── Tool Handlers ─────────────────────────────────────────────────────────────
@server.call_tool()
async def call_tool(
    name: str,
    arguments: dict
) -> list[types.TextContent]:
    """Handle all tool calls from Claude."""

    # ── NOTES ─────────────────────────────────────────────────────────────────

    if name == "add_note":
        notes     = load_json(NOTES_FILE)
        note_id   = f"note_{len(notes) + 1}_{datetime.now().strftime('%H%M%S')}"
        tags      = [t.strip() for t in arguments.get("tags", "").split(",") if t.strip()]

        note = {
            "id":         note_id,
            "title":      arguments["title"],
            "content":    arguments["content"],
            "tags":       tags,
            "created_at": get_timestamp(),
            "updated_at": get_timestamp()
        }

        notes.append(note)
        save_json(NOTES_FILE, notes)

        return [types.TextContent(
            type="text",
            text=f"✅ Note added successfully!\n"
                 f"ID     : {note_id}\n"
                 f"Title  : {note['title']}\n"
                 f"Tags   : {', '.join(tags) if tags else 'none'}\n"
                 f"Created: {note['created_at']}"
        )]

    elif name == "list_notes":
        notes      = load_json(NOTES_FILE)
        tag_filter = arguments.get("tag", "").strip()

        if tag_filter:
            notes = [n for n in notes if tag_filter in n.get("tags", [])]

        if not notes:
            return [types.TextContent(
                type="text",
                text="📭 No notes found."
            )]

        lines = [f"📝 Notes ({len(notes)} total):\n"]
        for note in notes:
            tags = ", ".join(note.get("tags", [])) or "no tags"
            lines.append(
                f"• [{note['id']}] {note['title']}\n"
                f"  Tags: {tags} | Created: {note['created_at']}\n"
            )

        return [types.TextContent(type="text", text="\n".join(lines))]

    elif name == "read_note":
        notes   = load_json(NOTES_FILE)
        note_id = arguments["note_id"]
        note    = next((n for n in notes if n["id"] == note_id), None)

        if not note:
            return [types.TextContent(
                type="text",
                text=f"❌ Note '{note_id}' not found."
            )]

        tags = ", ".join(note.get("tags", [])) or "none"
        return [types.TextContent(
            type="text",
            text=f"📝 {note['title']}\n"
                 f"{'─' * 40}\n"
                 f"{note['content']}\n"
                 f"{'─' * 40}\n"
                 f"ID      : {note['id']}\n"
                 f"Tags    : {tags}\n"
                 f"Created : {note['created_at']}\n"
                 f"Updated : {note['updated_at']}"
        )]

    elif name == "update_note":
        notes   = load_json(NOTES_FILE)
        note_id = arguments["note_id"]
        note    = next((n for n in notes if n["id"] == note_id), None)

        if not note:
            return [types.TextContent(
                type="text",
                text=f"❌ Note '{note_id}' not found."
            )]

        if "title"   in arguments: note["title"]      = arguments["title"]
        if "content" in arguments: note["content"]    = arguments["content"]
        note["updated_at"] = get_timestamp()

        save_json(NOTES_FILE, notes)
        return [types.TextContent(
            type="text",
            text=f"✅ Note '{note_id}' updated successfully!\n"
                 f"Title  : {note['title']}\n"
                 f"Updated: {note['updated_at']}"
        )]

    elif name == "delete_note":
        notes     = load_json(NOTES_FILE)
        note_id   = arguments["note_id"]
        new_notes = [n for n in notes if n["id"] != note_id]

        if len(new_notes) == len(notes):
            return [types.TextContent(
                type="text",
                text=f"❌ Note '{note_id}' not found."
            )]

        save_json(NOTES_FILE, new_notes)
        return [types.TextContent(
            type="text",
            text=f"🗑️ Note '{note_id}' deleted successfully!"
        )]

    elif name == "search_notes":
        notes   = load_json(NOTES_FILE)
        keyword = arguments["keyword"].lower()
        results = [
            n for n in notes
            if keyword in n["title"].lower()
            or keyword in n["content"].lower()
        ]

        if not results:
            return [types.TextContent(
                type="text",
                text=f"🔍 No notes found matching '{keyword}'"
            )]

        lines = [f"🔍 Found {len(results)} note(s) matching '{keyword}':\n"]
        for note in results:
            lines.append(
                f"• [{note['id']}] {note['title']}\n"
                f"  {note['content'][:100]}...\n"
            )

        return [types.TextContent(type="text", text="\n".join(lines))]

    # ── TODOS ──────────────────────────────────────────────────────────────────

    elif name == "add_todo":
        todos   = load_json(TODOS_FILE)
        todo_id = f"todo_{len(todos) + 1}_{datetime.now().strftime('%H%M%S')}"

        todo = {
            "id":         todo_id,
            "task":       arguments["task"],
            "priority":   arguments.get("priority", "medium"),
            "status":     "pending",
            "due_date":   arguments.get("due_date", None),
            "created_at": get_timestamp(),
            "completed_at": None
        }

        todos.append(todo)
        save_json(TODOS_FILE, todos)

        return [types.TextContent(
            type="text",
            text=f"✅ Todo added!\n"
                 f"ID      : {todo_id}\n"
                 f"Task    : {todo['task']}\n"
                 f"Priority: {todo['priority']}\n"
                 f"Due     : {todo['due_date'] or 'not set'}"
        )]

    elif name == "list_todos":
        todos           = load_json(TODOS_FILE)
        status_filter   = arguments.get("status", "all")
        priority_filter = arguments.get("priority", "")

        if status_filter != "all":
            todos = [t for t in todos if t["status"] == status_filter]
        if priority_filter:
            todos = [t for t in todos if t["priority"] == priority_filter]

        if not todos:
            return [types.TextContent(
                type="text",
                text="📭 No todos found."
            )]

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        todos.sort(key=lambda x: priority_order.get(x["priority"], 1))

        priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        status_icons   = {"pending": "⏳", "completed": "✅"}

        lines = [f"📋 Todos ({len(todos)} total):\n"]
        for todo in todos:
            p_icon = priority_icons.get(todo["priority"], "⚪")
            s_icon = status_icons.get(todo["status"], "❓")
            due    = f" | Due: {todo['due_date']}" if todo.get("due_date") else ""
            lines.append(
                f"{s_icon} {p_icon} [{todo['id']}] {todo['task']}{due}\n"
            )

        return [types.TextContent(type="text", text="\n".join(lines))]

    elif name == "complete_todo":
        todos   = load_json(TODOS_FILE)
        todo_id = arguments["todo_id"]
        todo    = next((t for t in todos if t["id"] == todo_id), None)

        if not todo:
            return [types.TextContent(
                type="text",
                text=f"❌ Todo '{todo_id}' not found."
            )]

        todo["status"]       = "completed"
        todo["completed_at"] = get_timestamp()
        save_json(TODOS_FILE, todos)

        return [types.TextContent(
            type="text",
            text=f"✅ Todo completed!\n"
                 f"Task       : {todo['task']}\n"
                 f"Completed  : {todo['completed_at']}"
        )]

    elif name == "delete_todo":
        todos     = load_json(TODOS_FILE)
        todo_id   = arguments["todo_id"]
        new_todos = [t for t in todos if t["id"] != todo_id]

        if len(new_todos) == len(todos):
            return [types.TextContent(
                type="text",
                text=f"❌ Todo '{todo_id}' not found."
            )]

        save_json(TODOS_FILE, new_todos)
        return [types.TextContent(
            type="text",
            text=f"🗑️ Todo '{todo_id}' deleted successfully!"
        )]

    elif name == "get_summary":
        notes = load_json(NOTES_FILE)
        todos = load_json(TODOS_FILE)

        pending   = [t for t in todos if t["status"] == "pending"]
        completed = [t for t in todos if t["status"] == "completed"]
        high      = [t for t in pending if t["priority"] == "high"]
        medium    = [t for t in pending if t["priority"] == "medium"]
        low       = [t for t in pending if t["priority"] == "low"]

        # Get all tags
        all_tags = []
        for note in notes:
            all_tags.extend(note.get("tags", []))
        unique_tags = list(set(all_tags))

        summary = f"""
📊 Summary
{'═' * 40}

📝 NOTES
  Total notes   : {len(notes)}
  Tags used     : {', '.join(unique_tags) if unique_tags else 'none'}

📋 TODOS
  Total todos   : {len(todos)}
  ⏳ Pending    : {len(pending)}
  ✅ Completed  : {len(completed)}

🎯 PENDING BY PRIORITY
  🔴 High       : {len(high)}
  🟡 Medium     : {len(medium)}
  🟢 Low        : {len(low)}
{'═' * 40}
"""
        if high:
            summary += "\n🔴 HIGH PRIORITY TASKS:\n"
            for t in high:
                due = f" (due: {t['due_date']})" if t.get("due_date") else ""
                summary += f"  • {t['task']}{due}\n"

        return [types.TextContent(type="text", text=summary)]

    # Unknown tool
    return [types.TextContent(
        type="text",
        text=f"❌ Unknown tool: {name}"
    )]

# ── Run Server ────────────────────────────────────────────────────────────────
def main():
    import asyncio
    
    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    
    asyncio.run(run())

if __name__ == "__main__":
    main()