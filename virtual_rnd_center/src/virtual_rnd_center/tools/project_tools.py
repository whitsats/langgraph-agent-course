import os
import sys
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict

class FileOperation(BaseModel):
    path: str = Field(..., description="The relative path to the file inside the project.")
    content: str = Field(..., description="The content.")

import re

class ScaffolderInput(BaseModel):
    project_root: str = Field(..., description="The project subdirectory (e.g., 'mvp_project', 'enterprise_project').")
    file_data: str = Field(
        ..., 
        description=(
            "A single string containing the paths and contents for one or more files. "
            "To avoid JSON escaping errors, do NOT use a JSON array. Instead, format this string exactly like this:\n\n"
            "### FILE: relative/path/to/file1.py\n"
            "```\n"
            "file contents here...\n"
            "```\n\n"
            "### FILE: relative/path/to/file2.md\n"
            "```\n"
            "file contents here...\n"
            "```\n"
        )
    )

class ProjectScaffolderTool(BaseTool):
    name: str = "project_scaffolder"
    description: str = "Builds project files. Avoids JSON escaping errors by using a specific markdown format for file_data."
    args_schema: type[BaseModel] = ScaffolderInput

    def _run(self, project_root: str, file_data: str) -> str:
        summary = []
        
        # --- IRON CAGE PATH RESOLUTION ---
        current_file_path = os.path.abspath(__file__)
        project_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file_path))))
        output_base = os.path.join(project_base, "output")
        
        # Sanitize project_root to prevent escaping
        safe_project_root = os.path.normpath(project_root.lstrip("/\\"))
        if ".." in safe_project_root:
            return "Error: Path traversal detected. You must use the provided project_root."
        
        # If the agent erroneously included 'output/' in the path, strip it
        if safe_project_root.startswith("output" + os.sep):
            safe_project_root = safe_project_root[7:]
        elif safe_project_root == "output":
            safe_project_root = ""
            
        target_dir = os.path.join(output_base, safe_project_root)
        
        print(f"[SCAFFOLDER] ANCHORED AT -> {target_dir}", flush=True)

        try:
            os.makedirs(target_dir, exist_ok=True)
            
            parts = file_data.split("### FILE:")
            for part in parts:
                if not part.strip():
                    continue
                
                # Split the part into the first line (path) and the rest (content)
                lines = part.strip().split("\n", 1)
                if len(lines) < 2:
                    continue
                
                path = lines[0].strip()
                content = lines[1]
                
                # Strip markdown code block wrappers if present
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[-1]  # remove the ```lang line
                    if content.endswith("```"):
                        content = content[:-3]            # remove the trailing ```
                
                # Further sanitize individual file paths
                clean_file_path = path.lstrip("/\\").replace("..", "")
                full_path = os.path.join(target_dir, clean_file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                with open(full_path, "w", encoding="utf-8", newline='\n') as f:
                    f.write(content)
                
                print(f"  [OK] Created: {path}", flush=True)
                summary.append(path)
            
            if not summary:
                return "Error: No files found in file_data. You MUST use the exact format:\n### FILE: path\n```\ncontent\n```"
            
            return f"Success. Created: {', '.join(summary)} in {target_dir}."
        except Exception as e:
            print(f"  [ERROR] {str(e)}", flush=True)
            return f"Error: {str(e)}"

