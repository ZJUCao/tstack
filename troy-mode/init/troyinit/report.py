"""The engine's report, as text or JSON (design section 3.3)."""

import json

from .plan import Plan


def to_dict(plan: Plan, dry_run: bool) -> dict:
    """Builds the JSON report of a plan.

    Args:
        plan: The planned step.
        dry_run: True when nothing was written.

    Returns:
        The report: ok, every file's action, conflicts, problems, the paths to
        stage, and the notes and next steps.
    """
    return {
        "command": plan.command,
        "ok": not plan.blocked,
        "dry_run": dry_run,
        "changed": plan.changed,
        "version": plan.version,
        "actions": [{"path": a.path, "action": a.action} for a in plan.actions],
        "conflicts": [{"path": p, "reason": r} for p, r in plan.conflicts],
        "problems": list(plan.problems),
        "stage": [] if plan.blocked else plan.stage(),
        "executable": [] if plan.blocked else plan.executable(),
        "hooks_path": plan.hooks_path,
        "email": plan.email,
        "differences": [{"path": p, "message": m} for p, m in plan.differences],
        "notes": list(plan.notes),
        "next_steps": [] if plan.blocked else list(plan.next_steps),
        **plan.extra,
    }


def to_json(plan: Plan, dry_run: bool) -> str:
    """Renders the JSON report, one object and a newline."""
    return json.dumps(to_dict(plan, dry_run), indent=2, ensure_ascii=False) + "\n"


def _result_line(plan: Plan, dry_run: bool) -> str:
    """Says how the step ended, in one line."""
    if plan.blocked:
        return "Stopped. Nothing changed."
    if not plan.changed:
        return "Nothing to change."
    return "Dry run: nothing changed." if dry_run else "Done."


def to_text(plan: Plan, dry_run: bool) -> str:
    """Renders the text report: problems, conflicts, actions, and next steps."""
    lines = [f"troy-init {plan.command}, {plan.plugin} {plan.version}"]
    lines += [f"problem   {p}" for p in plan.problems]
    lines += [f"conflict  {p}  {r}" for p, r in plan.conflicts]
    if not plan.blocked:
        lines += [f"{a.action:<9} {a.path}" for a in plan.actions if a.action != "keep"]
        kept = sum(1 for a in plan.actions if a.action == "keep")
        if kept:
            lines.append(f"keep      {kept} files unchanged")
    lines += [f"differs   {p}  {m}" for p, m in plan.differences]
    lines += [f"note      {n}" for n in plan.notes]
    if not plan.blocked:
        lines += [f"next      {s}" for s in plan.next_steps]
    lines.append(_result_line(plan, dry_run))
    return "\n".join(lines) + "\n"
