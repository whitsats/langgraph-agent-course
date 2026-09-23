"""
guard_tools.py — P0-3 / P2-1 Hardening Tools
==============================================
P0-3: ScopeGuardTool — reads boundary_manifest.md and extracts banned keywords,
      then validates any text block (architecture doc, code file) against them.
P2-1: CheckpointValidatorTool — verifies that a required artifact file exists
      on disk and is non-empty before allowing downstream tasks to proceed.
"""

import os
import re
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional

# ---------------------------------------------------------------------------
# Shared path helper
# ---------------------------------------------------------------------------

def _project_base() -> str:
    """Resolve the project root (4 levels up from this file)."""
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )


# ---------------------------------------------------------------------------
# P2-1: CheckpointValidatorTool
# ---------------------------------------------------------------------------

class CheckpointInput(BaseModel):
    file_path: str = Field(
        ...,
        description=(
            "Relative path from project root to the artifact file to validate. "
            "Example: 'output/mvp_project/boundary_manifest.md'"
        ),
    )
    min_bytes: Optional[int] = Field(
        default=200,
        description="Minimum file size in bytes to be considered non-empty. Default 200.",
    )


class CheckpointValidatorTool(BaseTool):
    name: str = "validate_checkpoint"
    description: str = (
        "Verifies that a required artifact file exists on disk and is large enough "
        "to be considered non-empty. Returns CHECKPOINT_OK or CHECKPOINT_FAIL. "
        "Call this at the START of every task to confirm the previous stage succeeded."
    )
    args_schema: type[BaseModel] = CheckpointInput

    def _run(self, file_path: str, min_bytes: int = 200) -> str:
        base = _project_base()
        full_path = os.path.join(base, file_path.lstrip("/\\"))

        print(f"[CHECKPOINT] Validating -> {full_path}", flush=True)

        if not os.path.exists(full_path):
            msg = f"CHECKPOINT_FAIL: File not found: {file_path}"
            print(f"  [FAIL] {msg}", flush=True)
            return msg

        size = os.path.getsize(full_path)
        if size < min_bytes:
            msg = (
                f"CHECKPOINT_FAIL: File exists but is too small "
                f"({size} bytes < {min_bytes} minimum): {file_path}"
            )
            print(f"  [FAIL] {msg}", flush=True)
            return msg

        msg = f"CHECKPOINT_OK: {file_path} ({size} bytes)"
        print(f"  [OK] {msg}", flush=True)
        return msg


# ---------------------------------------------------------------------------
# P0-3: ScopeGuardTool
# ---------------------------------------------------------------------------

class ScopeGuardInput(BaseModel):
    content: str = Field(
        ...,
        description=(
            "The text content to validate against the boundary manifest's banned keywords. "
            "Pass the full body of the generated architecture doc or code file."
        ),
    )
    manifest_path: Optional[str] = Field(
        default="output/mvp_project/boundary_manifest.md",
        description="Relative path to the boundary manifest file.",
    )


class ScopeGuardTool(BaseTool):
    name: str = "scope_guard_validator"
    description: str = (
        "Validates that a piece of generated content (architecture doc or code) "
        "does NOT contain any features that were ruled OUT-OF-SCOPE in the "
        "boundary_manifest.md. Returns SCOPE_OK or SCOPE_VIOLATION with details. "
        "ALWAYS call this before finalising any architecture or code output."
    )
    args_schema: type[BaseModel] = ScopeGuardInput

    # Hard-coded universal banned patterns (supplement boundary_manifest dynamic list).
    # These cover the most common LLM "auto-fill" features for social-media prompts.
    # They act as a safety net even when boundary_manifest.md is missing.
    # Rely entirely on the boundary_manifest.md dynamic BANNED IMPLEMENTATION KEYWORDS.
    # Hardcoded universal lists cause false positives in non-social-media projects.
    _UNIVERSAL_BANNED: list = []

    def _run(self, content: str, manifest_path: str = "output/mvp_project/boundary_manifest.md") -> str:
        base = _project_base()
        full_manifest = os.path.join(base, manifest_path.lstrip("/\\"))

        print(f"[SCOPE GUARD] Checking content against {full_manifest}", flush=True)

        # --- Extract banned keywords from manifest ---
        dynamic_banned: list[str] = []
        if os.path.exists(full_manifest):
            with open(full_manifest, "r", encoding="utf-8", errors="replace") as f:
                manifest_text = f.read()

            # Look for OUT-OF-SCOPE lines and BANNED IMPLEMENTATION KEYWORDS section
            oos_pattern = re.compile(r"-\s*\[\s*\]\s*OUT-OF-SCOPE[:\s]+(.+)", re.IGNORECASE)
            banned_section = re.search(
                r"##\s*[\d\.]*\s*BANNED IMPLEMENTATION KEYWORDS\s*\n(.+?)(?:\n##|\Z)",
                manifest_text,
                re.DOTALL | re.IGNORECASE,
            )

            for match in oos_pattern.finditer(manifest_text):
                # Extract feature name (first word)
                feature_word = match.group(1).strip().split()[0].rstrip(",:;")
                if len(feature_word) > 2:
                    dynamic_banned.append(feature_word)

            if banned_section:
                keywords_text = banned_section.group(1).strip()
                for kw in re.split(r"[,\s]+", keywords_text):
                    kw = kw.strip().strip(".,;:")
                    if len(kw) > 2:
                        dynamic_banned.append(kw)
        else:
            print(f"  [SCOPE GUARD] Warning: Manifest not found, using universal banned list only.", flush=True)

        all_banned = list(set(self._UNIVERSAL_BANNED + dynamic_banned))

        # --- Scan content with word boundaries to prevent false positives ---
        violations = []
        for kw in all_banned:
            # Escape kw to avoid regex injection, then use word boundaries
            pattern = re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            if pattern.search(content):
                violations.append(kw)

        if violations:
            msg = (
                f"SCOPE_VIOLATION: The following OUT-OF-SCOPE keywords were found in the output: "
                f"{violations}. "
                f"You MUST remove all references to these features and regenerate the content. "
                f"Re-read boundary_manifest.md Section 2 (OUT-OF-SCOPE) for guidance."
            )
            print(f"  [VIOLATION] {msg}", flush=True)
            return msg

        msg = f"SCOPE_OK: Content passed scope validation. ({len(all_banned)} keywords checked)"
        print(f"  [OK] {msg}", flush=True)
        return msg
