"""Knowledge-batch iteration folders under ai-batches/<slug>/iterations/."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


ACCEPTANCE_STUB = """# Acceptance criteria

- [ ] No step errors in run_report.json
- [ ] Fail screenshots reviewed (or none)
- [ ] OCR / UI state matches the goal
- [ ] Ready to promote steps into Loops events (optional)

Max iterations: set in Notes or stop manually with Stop all.
"""

PROBE_ACCEPTANCE_STUB = """# Probe acceptance

- [ ] QUESTION.md is still the question this run answered
- [ ] No unexpected step errors in run_report.json (misses are data — note them)
- [ ] Linked Screen Map shots are enough to answer the question without Eric narrating
- [ ] reflection.md (this iteration or next chat) states: answered / partial / blocked + next probe

Max iterations: keep short. Prefer a new probe over endlessly retuning one batch.
"""

QUESTION_STUB = """# Question

What are we trying to learn from this Start?

(One sentence. Evidence goes in the linked Screen Map + run_report.json.)
"""

REFLECTION_STUB = """# Reflection

- Verdict: answered | partial | blocked
- What the shots / report show:
- What to change next (coords, ensure_*, new probe, playbook note):
"""


def iterations_root(batch_dir: Path) -> Path:
    return Path(batch_dir) / "iterations"


def next_iteration_index(batch_dir: Path) -> int:
    root = iterations_root(batch_dir)
    if not root.is_dir():
        return 1
    highest = 0
    for child in root.iterdir():
        if child.is_dir() and child.name.isdigit():
            highest = max(highest, int(child.name))
    return highest + 1


def _batch_genre(batch_dir: Path, *, batch_json_name: str = "batch.json") -> str:
    path = Path(batch_dir) / batch_json_name
    if not path.is_file():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("genre") or "").strip().lower()


def ensure_acceptance(batch_dir: Path, *, genre: str | None = None) -> Path:
    path = Path(batch_dir) / "ACCEPTANCE.md"
    if path.is_file():
        return path
    resolved = (genre or _batch_genre(batch_dir) or "").strip().lower()
    stub = PROBE_ACCEPTANCE_STUB if resolved == "probe" else ACCEPTANCE_STUB
    path.write_text(stub, encoding="utf-8")
    return path


def ensure_probe_scaffold(batch_dir: Path) -> dict[str, Path]:
    """Write QUESTION.md / ACCEPTANCE.md for genre=probe batches (never overwrite)."""

    batch_dir = Path(batch_dir)
    written: dict[str, Path] = {}
    question = batch_dir / "QUESTION.md"
    if not question.is_file():
        question.write_text(QUESTION_STUB, encoding="utf-8")
        written["question"] = question
    written["acceptance"] = ensure_acceptance(batch_dir, genre="probe")
    return written


def begin_iteration(batch_dir: Path, *, batch_json_name: str = "batch.json") -> Path:
    """Create iterations/NNN/ with a copy of batch.json. Returns iteration dir."""

    batch_dir = Path(batch_dir)
    genre = _batch_genre(batch_dir, batch_json_name=batch_json_name)
    if genre == "probe":
        ensure_probe_scaffold(batch_dir)
    else:
        ensure_acceptance(batch_dir, genre=genre)
    index = next_iteration_index(batch_dir)
    dest = iterations_root(batch_dir) / f"{index:03d}"
    dest.mkdir(parents=True, exist_ok=False)
    src = batch_dir / batch_json_name
    if src.is_file():
        shutil.copy2(src, dest / batch_json_name)
    meta = {
        "iteration": index,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "batch_dir": str(batch_dir),
        "genre": genre or None,
    }
    (dest / "iteration.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return dest


def finalize_iteration(
    iteration_dir: Path,
    *,
    run_report: dict[str, Any] | Path | None = None,
    screen_map_slug: str | None = None,
    reflection: str | None = None,
) -> None:
    iteration_dir = Path(iteration_dir)
    if run_report is not None:
        if isinstance(run_report, Path):
            if run_report.is_file():
                shutil.copy2(run_report, iteration_dir / "run_report.json")
        else:
            (iteration_dir / "run_report.json").write_text(
                json.dumps(run_report, indent=2), encoding="utf-8"
            )
    meta_path = iteration_dir / "iteration.json"
    meta: dict[str, Any] = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    meta["finished_at"] = datetime.now().isoformat(timespec="seconds")
    if screen_map_slug:
        meta["screen_map_slug"] = screen_map_slug
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if reflection is not None:
        (iteration_dir / "reflection.md").write_text(reflection.strip() + "\n", encoding="utf-8")
    elif str(meta.get("genre") or "").strip().lower() == "probe":
        if not (iteration_dir / "reflection.md").is_file():
            (iteration_dir / "reflection.md").write_text(REFLECTION_STUB, encoding="utf-8")
