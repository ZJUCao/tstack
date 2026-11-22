"""A stand-in for the Claude Code CLI in the F16 end-to-end tests (design 14.1).

It never calls a model and never uses the network. The tests copy it into a
folder of its own, beside a plan.json that says how it behaves, and set
TROY_EXAM_CLI to the copy. Each call claims the next number of its kind
(role or judge) with an exclusive file, records what it saw in
calls/<kind>-<n>.json, and answers:

- ``--version``: prints a version line.
- With ``--json-schema``: acts as the judge (design 11.4). It reads its
  folder, passes each label whose report.md holds the plan's pass marker and
  fails the others (all inverted on the calls the plan names), and prints one
  JSON object with structured_output, total_cost_usd, and modelUsage.
- Otherwise: acts as the driver session (design 11.3). It takes the brief from
  between the BEGIN and END lines of -p, writes the mock of F01 in its current
  folder, writes the role's transcript and meta under
  $CLAUDE_CONFIG_DIR/projects/<folder key>/<session ID>/subagents/, and prints
  stream-json that ends in a result event.

A role call's behavior is the plan's "role", updated in this order by:

- "versions": for the version the call runs, named by the last "Marker:"
  line of its agent file ("none" for a file without one), and again for
  "<marker>@<case branch>": that entry's "every" for each of its calls, then
  its "calls" entry for the version's own n-th call, counted from 1 with
  claims of its own (v-<key>-<n>.claim, which claims("role") does not count).
  So a test can make the head's first two runs fail, or one case's runs cost
  more, whatever order the exam runs them in.
- "calls": the entry for the call's number among all role calls.

The keys a behavior may hold: "edit", "report" (handback, text, or
alternate), "probe", "role_model", "costs" (model ID to dollars), "result"
("limit" for a usage limit), "brief" ("mangle" changes the brief, so the run
is void), and "tidy" (false leaves the pass marker out of the report, so the
judge fails the run while it still counts). A plan without "versions" or
"tidy" behaves as before.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "calls"
MOCK = ('"""Counts words in a text (F01)."""\n\n\ndef count(text: str) -> int:\n'
        '    """Counts the words of a text.\n\n    Args:\n        text: The text.\n\n'
        '    Returns:\n        The number of words.\n    """\n    raise NotImplementedError\n')


def option(args, name):
    """The word after an option, or None."""
    if name in args and args.index(name) + 1 < len(args):
        return args[args.index(name) + 1]
    return None


def claim(kind):
    """Claims the next call number of a kind with an exclusive file."""
    LOG.mkdir(exist_ok=True)
    number = 1
    while True:
        try:
            handle = os.open(str(LOG / f"{kind}-{number:03d}.claim"),
                             os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(handle)
            return number
        except FileExistsError:
            number += 1


def folder_key(path):
    """The CLI's project folder key: every character but ASCII letters and digits becomes -."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def quiet(command, cwd):
    """Runs a command and returns (exit code, stdout, stderr)."""
    try:
        proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", stdin=subprocess.DEVNULL, timeout=60, check=False)
    except OSError as exc:
        return [127, "", str(exc)]
    return [proc.returncode, proc.stdout, proc.stderr]


def brief_of(prompt):
    """The text between the line BEGIN and the last line END, or None."""
    lines = prompt.split("\n")
    if "BEGIN" not in lines or "END" not in lines:
        return None
    begin = lines.index("BEGIN")
    end = len(lines) - 1 - lines[::-1].index("END")
    return "\n".join(lines[begin + 1:end])


def write_lf_preserving(path, text):
    """Writes text with the line ends the file had (CRLF stays CRLF)."""
    old = path.read_bytes() if path.exists() else b""
    data = text.encode("utf-8")
    if b"\r\n" in old:
        data = data.replace(b"\n", b"\r\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def probe_gh(cwd):
    """Runs the gh commands a role uses, and two it may not, through the PATH."""
    gh = shutil.which("gh", path=os.environ.get("PATH", ""))
    if gh is None:
        return {"found": None}
    found = {"found": gh}
    for name, args in (("view", ["pr", "view", "--json", "number,headRefName"]),
                       ("checks", ["pr", "checks"]),
                       ("comment", ["pr", "comment", "1", "--body", "hi"]),
                       ("api", ["api", "repos/o/r"])):
        found[name] = quiet([gh, *args], cwd)
    return found


def report_text(cwd, plugin, mangled, tidy=True):
    """The role's report in the Developer's format, naming the run's own folders."""
    summary = "kept tidy; the mock is written" if tidy and not mangled else "the mock is written"
    return ("Role: Developer\nTask: DV1, F01\nResult: done\n"
            "Changed files: src/wordcount/f01.py\n"
            f"Checks: ran in {cwd} with {plugin}\n"
            f"Summary: {summary}.\nFindings: None\nQuestion: None\n")


def transcript_lines(brief, cwd, report, how):
    """The role's transcript: the brief, a read of the rules, git status, the write, the end."""
    rules = os.path.join(cwd, "docs", "rules.md")
    target = os.path.join(cwd, "src", "wordcount", "f01.py")

    def line(kind, content, **extra):
        """One transcript line."""
        return json.dumps({"type": kind, "isSidechain": True, "uuid": str(uuid.uuid4()),
                           "message": {"role": kind, "content": content}, **extra})

    def use(name, data, use_id):
        """A tool_use block."""
        return {"type": "tool_use", "id": use_id, "name": name, "input": data}

    def done(use_id):
        """A tool_result block."""
        return [{"type": "tool_result", "tool_use_id": use_id, "content": "ok"}]

    lines = [line("user", brief),
             json.dumps({"type": "attachment", "attachment": {"type": "skill_listing"}}),
             line("assistant", [{"type": "text", "text": "I read the rules first."},
                                use("Read", {"file_path": rules}, "t1")]),
             line("user", done("t1")),
             line("assistant", [use("Bash", {"command": "git status --short"}, "t2")]),
             line("user", done("t2")),
             line("assistant", [use("Write", {"file_path": target, "content": MOCK}, "t3")]),
             line("user", done("t3"))]
    if how == "handback":
        lines.append(line("assistant", [use("SubagentHandback", {"message": report}, "t4")]))
    else:
        lines.append(line("assistant", [{"type": "text", "text": report}]))
    return lines


def version_behavior(plan, marker, branch):
    """The plan's behavior for one version's call, and that version's call numbers by key.

    Returns:
        (behavior, numbers): the "versions" entries for the marker and for
        "<marker>@<branch>", every-call part first, then the n-th call's part;
        and each key mapped to n.
    """
    found, numbers = {}, {}
    versions = plan.get("versions") or {}
    for key in (marker, f"{marker}@{branch}"):
        entry = versions.get(key)
        if not entry:
            continue
        number = claim("v-" + re.sub(r"[^A-Za-z0-9]", "-", key))
        numbers[key] = number
        found.update(entry.get("every", {}))
        found.update(entry.get("calls", {}).get(str(number), {}))
    return found, numbers


def role(args, plan):
    """Acts as the driver session and its role."""
    number = claim("role")
    cwd = os.getcwd()
    prompt = option(args, "-p") or ""
    plugin = option(args, "--plugin-dir") or ""
    session = option(args, "--session-id") or str(uuid.uuid4())
    brief = brief_of(prompt)
    agent = Path(plugin) / "agents" / "troy-developer.md"
    markers = re.findall(r"(?m)^Marker: (\S+)", agent.read_text(encoding="utf-8")) \
        if agent.is_file() else ["no-agent-file"]
    marker = markers[-1] if markers else "none"
    branch = quiet(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)[1].strip()
    behavior = dict(plan.get("role", {}))
    by_version, numbers = version_behavior(plan, marker, branch)
    behavior.update(by_version)
    behavior.update(plan.get("calls", {}).get(str(number), {}))
    seen = {"kind": "role", "index": number, "argv": args, "cwd": cwd, "env": dict(os.environ),
            "brief": brief, "start": time.time(), "behavior": behavior, "marker": marker,
            "branch": branch, "version_calls": numbers}
    seen["run_root"] = sorted(os.listdir(Path(cwd).parent))
    if behavior.get("probe"):
        seen["gh"] = probe_gh(cwd)
    later = plan.get("later")
    if later:
        origin = quiet(["git", "remote", "get-url", "origin"], cwd)[1].strip()
        seen["later_in_project"] = quiet(["git", "cat-file", "-e", later + "^{commit}"], cwd)[0]
        seen["later_in_origin"] = quiet(["git", "--git-dir", origin, "cat-file", "-e",
                                         later + "^{commit}"], cwd)[0]
    result = behavior.get("result", "success")
    costs = behavior.get("costs", {})
    if result == "limit":
        write_seen(seen)
        event = {"type": "result", "subtype": "success", "is_error": True,
                 "result": "You've hit your 5-hour limit · resets 3pm", "session_id": session,
                 "total_cost_usd": 0.0, "modelUsage": {}}
        print(json.dumps(event))
        return 1
    mangled = behavior.get("brief") == "mangle"
    first = brief if not mangled else (brief or "").replace("Task: DV1", "Task: DV2", 1)
    if behavior.get("edit", True):
        write_lf_preserving(Path(cwd) / "src" / "wordcount" / "f01.py", MOCK)
    report = report_text(cwd, plugin, mangled, behavior.get("tidy", True))
    how = behavior.get("report", "handback")
    if how == "alternate":
        how = "handback" if number % 2 else "text"
    seen["report_how"] = how
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    subagents = config / "projects" / folder_key(cwd) / session / "subagents"
    subagents.mkdir(parents=True, exist_ok=True)
    agent_id = uuid.uuid4().hex[:16]
    (subagents / f"agent-{agent_id}.jsonl").write_text(
        "\n".join(transcript_lines(first or "", cwd, report, how)) + "\n", encoding="utf-8")
    agent_type = (re.findall(r"tstack:troy-[a-z-]+", prompt) or ["tstack:troy-developer"])[0]
    (subagents / f"agent-{agent_id}.meta.json").write_text(
        json.dumps({"agentType": agent_type, "model": behavior.get("role_model", "sonnet")}),
        encoding="utf-8")
    seen["transcript_folder"] = str(subagents)
    write_seen(seen)
    print(json.dumps({"type": "system", "subtype": "init", "session_id": session,
                      "model": option(args, "--model")}))
    print(json.dumps({"type": "assistant", "session_id": session,
                      "message": {"content": [{"type": "text", "text": report}]}}))
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                      "duration_ms": 1200, "num_turns": 2, "result": report,
                      "session_id": session, "total_cost_usd": round(sum(costs.values()), 6),
                      "modelUsage": {model: {"inputTokens": 100, "outputTokens": 50,
                                             "costUSD": cost} for model, cost in costs.items()}}))
    return 0


def judge(args, plan):
    """Acts as the judge: grades each label by the plan's pass marker."""
    number = claim("judge")
    settings = plan.get("judge", {})
    cwd = Path.cwd()
    files = sorted(p.relative_to(cwd).as_posix() for p in cwd.rglob("*") if p.is_file())
    contents = {name: (cwd / name).read_text(encoding="utf-8", errors="replace")
                for name in files}
    count = len(re.findall(r"(?m)^\d+\. ", contents.get("rubric.md", "")))
    labels = sorted(p.name for p in cwd.iterdir() if p.is_dir())
    invert = number in settings.get("misgrade", [])
    marker = settings.get("pass_marker", "")
    sets = []
    for label in labels:
        report = contents.get(f"{label}/report.md", "")
        passed = (marker in report) != invert
        sets.append({"label": label, "criteria": [
            {"id": i, "pass": passed, "evidence": f"The report says: \"{report[:40]}\""}
            for i in range(1, count + 1)]})
    write_seen({"kind": "judge", "index": number, "argv": args, "cwd": str(cwd), "files": files,
                "contents": contents, "labels": labels, "inverted": invert,
                "env": dict(os.environ)})
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                      "result": "Graded.", "session_id": str(uuid.uuid4()),
                      "total_cost_usd": 0.5, "modelUsage": {"claude-opus-4-1-20250805":
                                                            {"costUSD": 0.5}},
                      "structured_output": {"sets": sets}}))
    return 0


def write_seen(seen):
    """Records one call's observations."""
    name = f"{seen['kind']}-{seen['index']:03d}.json"
    (LOG / name).write_text(json.dumps(seen, indent=1), encoding="utf-8")


def main():
    """Answers one call as the plan says."""
    args = sys.argv[1:]
    if "--version" in args:
        print("2.1.325 (Claude Code)")
        return 0
    plan = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))
    if "--json-schema" in args:
        return judge(args, plan)
    return role(args, plan)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001  (record the error for the test's message, then fail)
        LOG.mkdir(exist_ok=True)
        (LOG / f"{os.getpid()}.error").write_text(traceback.format_exc(), encoding="utf-8")
        raise
