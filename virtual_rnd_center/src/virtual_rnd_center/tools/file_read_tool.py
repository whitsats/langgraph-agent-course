import os
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional

class FileReadInput(BaseModel):
    file_path: str = Field(
        ...,
        description=(
            "The FULL relative path to a specific FILE to read, starting from the project root. "
            "Example: 'output/mvp_project/boundary_manifest.md'. "
            "IMPORTANT: You must provide a path to a FILE, not a directory."
        ),
    )
    start_line: Optional[int] = Field(default=1, description="Line number to start reading from (1-indexed).")
    line_count: Optional[int] = Field(default=None, description="Number of lines to read. If omitted, reads entire file.")


class FileReadTool(BaseTool):
    name: str = "read_file_content"
    description: str = (
        "Reads the content of a specific FILE. "
        "Provide the full relative path from the project root to the file, "
        "e.g. 'output/mvp_project/boundary_manifest.md'. "
        "Supports chunked reading via start_line and line_count. "
        "Returns an error string if the file is not found or the path is a directory."
    )
    args_schema: type[BaseModel] = FileReadInput

    def _run(
        self,
        file_path: str,
        start_line: int = 1,
        line_count: Optional[int] = None,
    ) -> str:
        # ----------------------------------------------------------------
        # 1. Path resolution — anchor to project root
        # ----------------------------------------------------------------
        if not os.path.isabs(file_path):
            current_file = os.path.abspath(__file__)
            # src/virtual_rnd_center/tools/file_read_tool.py -> 4 levels up
            project_base = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            )
            file_path = os.path.abspath(os.path.join(project_base, file_path))

        print(f"[READ] {file_path}", flush=True)

        # ----------------------------------------------------------------
        # 2. Guard: directory path (root cause of Permission denied on Windows)
        # ----------------------------------------------------------------
        if os.path.isdir(file_path):
            # List directory contents to help the agent correct itself
            try:
                entries = os.listdir(file_path)
                listing = "\n".join(f"  - {e}" for e in sorted(entries)[:30])
            except Exception:
                listing = "(could not list)"
            return (
                f"Error: '{file_path}' is a DIRECTORY, not a file. "
                f"You must specify a path to a specific FILE (e.g., add the filename at the end).\n"
                f"Contents of this directory:\n{listing}"
            )

        # ----------------------------------------------------------------
        # 3. Guard: file not found
        # ----------------------------------------------------------------
        if not os.path.exists(file_path):
            return f"Error: File not found at path: {file_path}"

        # ----------------------------------------------------------------
        # 4. Read with chunking support
        # ----------------------------------------------------------------
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            start = max(0, start_line - 1)
            if line_count:
                end = start + line_count
                content = "".join(lines[start:end])
            else:
                content = "".join(lines[start:])

            total_lines = len(lines)
            print(f"  [OK] {total_lines} lines total, returning lines {start_line}-{start + (line_count or total_lines)}", flush=True)

            return content if content.strip() else "File is empty."

        except PermissionError:
            return (
                f"Error: Permission denied reading '{file_path}'. "
                "This usually means the path points to a directory, not a file. "
                "Please check the path and ensure it ends with a filename (e.g., 'boundary_manifest.md')."
            )
        except Exception as e:
            return f"Error reading file: {str(e)}"
