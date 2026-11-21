"""Python from standard input group (F05 design 7.1, 8.3, 10, 13.1, and D223; R23).

For every caller in a troy-mode project, the main session included, the
PreToolUse hook refuses a Bash or PowerShell command that runs Python with its
program read from standard input: ``python -`` (or ``python -- -``),
``python -i`` (alone or in a flag group), and Python with no script, ``-c``, or
``-m``, whatever feeds standard input. The runners ``mamba run``,
``micromamba run``, ``conda run``, ``uv run``, and ``pixi run`` are removed
first, ``timeout`` is a wrapper of design 7.1 for every check, and a command
that came through ``xargs`` is not refused for want of a script. The refusal
has rule ``python-stdin``; its log line holds no command text.

The tests are written from the design (version 1.4) and the interface note of
tstack #64 before the code exists. They are black-box, through hook_helpers.

Conventions, beyond those of hook_helpers.py.

1. A refused case asserts the deny, the note's form fragment (DASH,
   INTERACTIVE, or NO_SCRIPT, each starting with "R23:"), and the sentence
   that ends every R23 reason (END). ReasonTests asserts the whole reason of
   design 8.3's text block, with and without the scratchpad and the
   environment.
2. An allowed case asserts silence: exit code 0, nothing on stdout or stderr.
3. Table tests run their calls in parallel (run_many) in a project whose log
   no test reads. Tests that read the log build their own project and run one
   call at a time.

Planted bugs (design 13.2) and the tests that catch them. Each test also
names its bug in its docstring.

- python3 - missed, the -- - form missed, -i inside a flag group missed, and
  -W not skipping its value:
  RefusedFormTests.test_each_refused_form_is_refused.
- py -3.13 not skipped: RefusedFormTests.test_each_refused_form_is_refused
  (py -V:3.13 and py -V:3.13 -, which read as -V when the selector is not
  skipped).
- timeout not unwrapped: TimeoutTests.test_python_after_timeout_is_refused,
  ShellFormTests.test_refused_samples_inside_every_form, and
  TimeoutGitTests.test_git_writes_after_timeout_are_refused_for_subagents.
- xargs not exempt: XargsTests.test_xargs_python_without_a_script_passes.
- The main session not checked:
  RefusedFormTests.test_each_refused_form_is_refused (main session).
- The log line holding command text:
  LogTests.test_refusal_logs_rule_python_stdin_without_the_command.

Run from the repository root:
python -m unittest discover -s troy-mode/hooks/tests -p "test_python_stdin.py" -v
"""

import unittest

from hook_helpers import (
    ARCH, CR, DEV, ERROR_PREFIX, EXPLORE, FOO, GP, IFD, INVALID_CONFIG, LOG_KEYS, LOG_RULES,
    LOG_TIME, MAIN, PAD, SCRATCH, SESSION, TE, TM, HookTestCase, Project, bash_call,
    make_config, plain_folder, run_many, start_call,
)

# The note's section 1.1: the form each refusal names, for the first refused
# Python command of the line.
DASH = "R23: `python -` makes Python read its program from standard input"
INTERACTIVE = "R23: `python -i` makes Python read its program from standard input"
NO_SCRIPT = "R23: `python` with no script makes Python read its program from standard input"
HANG = "and such a run can hang at Python's interactive prompt."
PAD_PART = "Write the script to a file in the scratchpad ({pad}) and run that file"
NO_PAD_PART = "Write the script to a file in the scratchpad and run that file"
ENV_PART = ("with the project's Python (`[lang] environment` {env}), "
            "for example `python -X utf8 <file>`.")
NO_ENV_PART = "with the project's Python, for example `python -X utf8 <file>`."
END = "Python with a script file, `-c`, or `-m` may still read data from a pipe or `/dev/null`."

ENV_NAME = "tstack-pyenv"
ENV_CONFIG = make_config(extra=f'[lang]\nname = "python"\nenvironment = "{ENV_NAME}"\n')
# A unique word for the log tests; no other text in this file holds it.
MARKER = "TROYPYMARK-5e2b7d"

ROLES = (DEV, TE, ARCH, IFD, TM, CR)
# The note's section 1.3: the main session, a role, and another subagent.
THREE = (MAIN, DEV, GP)
EVERY = (MAIN, *ROLES, GP, EXPLORE, FOO)


def full_reason(form, pad=None, env=None):
    """Returns the whole R23 reason of design 8.3's text block.

    Args:
        form: DASH, INTERACTIVE, or NO_SCRIPT.
        pad: The scratchpad as given in the input, or None when it is left out.
        env: The committed ``[lang] environment``, or None when it is not set.

    Returns:
        The reason's text.
    """
    pad_part = NO_PAD_PART if pad is None else PAD_PART.format(pad=pad)
    env_part = NO_ENV_PART if env is None else ENV_PART.format(env=env)
    return f"{form}, {HANG} {pad_part} {env_part} {END}"


# Design 8.3 and the note's section 1.5: refused, with the form each names.
REFUSED = (
    ("python -", DASH),
    ("python3 -", DASH),
    ("python3.13 -", DASH),
    ("python3.11 -", DASH),
    ("py -", DASH),
    ("python.exe -", DASH),
    ("py.exe -", DASH),
    ("/usr/bin/python3 -", DASH),
    ('"C:/Program Files/Python313/python.exe" -', DASH),
    ("C:/Users/x/miniforge3/envs/tstack/python.exe -", DASH),
    ("'/c/Users/x/AppData/Local/Programs/Python/Python313/python.exe' -", DASH),
    ("python -- -", DASH),
    ("python -u -", DASH),
    ("python -I -", DASH),
    ("python -X utf8 -", DASH),
    ("python -W ignore -", DASH),
    ("python3 - < /dev/null", DASH),
    ("python - <<'EOF'\nprint(1)\nEOF", DASH),
    ("python3 - <<\"PY\"\nimport sys\nPY", DASH),
    ("py -3.13 -", DASH),
    ("py -3.13-64 -", DASH),
    ("py -V:3.13 -", DASH),
    ("PYTHONPATH=src python -", DASH),
    ("env python3 -", DASH),
    ("PY=python; $PY -", DASH),
    ("python -i", INTERACTIVE),
    ("python -i x.py", INTERACTIVE),
    ("python3 -i x.py", INTERACTIVE),
    ("python -ui x.py", INTERACTIVE),
    ("python -ic 'x'", INTERACTIVE),
    ("python -i -c 'x'", INTERACTIVE),
    ("python -i -m pytest", INTERACTIVE),
    ("python -i -", INTERACTIVE),
    ("python", NO_SCRIPT),
    ("python3", NO_SCRIPT),
    ("py", NO_SCRIPT),
    ("python -u", NO_SCRIPT),
    ("python --", NO_SCRIPT),
    ("python -Xutf8", NO_SCRIPT),
    ("python -X utf8", NO_SCRIPT),
    ("python -W ignore", NO_SCRIPT),
    ("python -Wignore", NO_SCRIPT),
    ("python --check-hash-based-pycs never", NO_SCRIPT),
    ("cat x.py | python3", NO_SCRIPT),
    ("echo 'print(1)' | python", NO_SCRIPT),
    ("python < /dev/null", NO_SCRIPT),
    ("python3 <<'EOF'\nimport sys\nEOF", NO_SCRIPT),
    ("py -V:3.13", NO_SCRIPT),
    ("py -3", NO_SCRIPT),
)

# The note's section 1.5: allowed, so silent.
ALLOWED = (
    "python x.py",
    "python3 x.py",
    "python x.py < /dev/null",
    "python3 x.py < input.txt",
    "echo '{}' | python -c \"import json,sys; json.load(sys.stdin)\"",
    "echo '{}' | python -X utf8 -c \"import json,sys; json.load(sys.stdin)\"",
    "python -c 'print(1)'",
    "python -c'print(1)'",
    "python -cpass",
    "python -Bc 'x'",
    "python -ci",
    "python -m pytest -q",
    "python -mpytest",
    "python -m json.tool < a.json",
    "python -X utf8 x.py",
    "python -Xutf8 x.py",
    "python -W ignore x.py",
    "python -Wignore x.py",
    "python --check-hash-based-pycs never x.py",
    "python --version",
    "python3 --version",
    "python -V",
    "python -VV",
    "python -h",
    "python --help",
    "python --help-env",
    "python -?",
    "python -- x.py",
    "python x.py -i",
    "python x.py -",
    "python -c 'x' -i",
    "python -m pytest -",
    "py -0",
    "py -0p",
    "py --list",
    "py --list-paths",
    "py -3.13 x.py",
    "py -3 -m pytest",
    "py -V:3.13 -c 'x'",
    "/usr/bin/python3 x.py",
    '"C:/Program Files/Python313/python.exe" -m pytest',
    "PYTHONPATH=src python -m pytest -q",
    "ls | xargs python",
    "pythonic -",
    "echo python -",
    "echo 'python -'",
    "grep -n 'python -' notes.md",
    "pip install x",
    "pip install ruff",
    "$PY -",
    '"$PY" -',
    "cat > x.py <<'EOF'\npython -\nEOF\npython x.py",
    "cat > notes.md <<'EOF'\nNever run python - or python -i.\nEOF",
    "ls -la",
)

# Design 8.3 and the note's section 1.4: runners with their options.
RUNNER_REFUSED = (
    ("mamba run -n env python -", DASH),
    ("mamba run -p /opt/envs/x python3 -", DASH),
    ("mamba run --name=env python -", DASH),
    ("micromamba run -n env python3 -", DASH),
    ("conda run -n env python -", DASH),
    ("conda run --no-capture-output -n env python -i x.py", INTERACTIVE),
    ("conda run --cwd src -n env python", NO_SCRIPT),
    ("uv run python -", DASH),
    ("uv run --with ruff python -", DASH),
    ("uv run --python 3.13 python -", DASH),
    ("uv run -- python -", DASH),
    ("pixi run python -", DASH),
    ("pixi run -e env python -", DASH),
    ("pixi run --manifest-path pixi.toml python3 -", DASH),
    ("mamba run -n env python -X utf8 - <<'EOF'\nprint(1)\nEOF", DASH),
    ("timeout 60 mamba run -n env python -", DASH),
)
RUNNER_ALLOWED = (
    "mamba run -n env python x.py",
    "mamba run -n env python -m pytest -q",
    "mamba run -p /opt/envs/x python3 --version",
    "micromamba run -n env python3 -c 'x'",
    "conda run -n env python -X utf8 x.py",
    "uv run python x.py",
    "uv run --with ruff python x.py",
    "uv run pytest -q",
    "pixi run python -m pytest",
    "pixi run -e env python x.py",
    "mamba run -n env pytest -q",
)

# Design 7.1 and the note's section 1.4: timeout with its options and duration.
TIMEOUT_FORMS = (
    "timeout 60 {c}",
    "timeout 2m {c}",
    "timeout 1.5 {c}",
    "timeout -s KILL 60 {c}",
    "timeout -k 5 60 {c}",
    "timeout --signal=TERM 60 {c}",
    "timeout --signal TERM 60 {c}",
    "timeout --kill-after=5 60 {c}",
    "timeout --kill-after 5 60 {c}",
    "timeout --preserve-status 60 {c}",
    "timeout --foreground 60 {c}",
    "timeout -v 60 {c}",
    "timeout --verbose 60 {c}",
    "timeout -- 60 {c}",
    "timeout -k 5 --signal=TERM --preserve-status 60 {c}",
)

# The note's section 1.4: xargs adds words, so no script is no refusal.
XARGS_REFUSED = (
    ("echo x | xargs python -", DASH),
    ("ls | xargs -n 1 python3 -", DASH),
    ("echo x.py | xargs python -i", INTERACTIVE),
)
XARGS_ALLOWED = (
    "ls *.py | xargs python",
    "ls | xargs python",
    "find . -name '*.py' | xargs -n 1 python3",
    "echo x.py | xargs python -u",
    "echo x.py | xargs python -X utf8",
)

# Design 7.1 and 13.1: the shell forms, as templates around a command.
FORMS = (
    ("alone", "{c}"),
    ("after &&", "ls && {c}"),
    ("before &&", "{c} && echo done"),
    ("after ;", "echo start; {c}"),
    ("before ;", "{c}; echo done"),
    ("after ||", "false || {c}"),
    ("after |", "echo y | {c}"),
    ("before |", "{c} | cat"),
    ("after &", "true & {c}"),
    ("after a line break", "echo start\n{c}"),
    ("in ( )", "({c})"),
    ("in $( )", 'echo "$({c})"'),
    ("in backticks", "echo `{c}`"),
    ("in bash -c", 'bash -c "{c}"'),
    ("in sh -c", "sh -c '{c}'"),
    ("in eval", 'eval "{c}"'),
    ("after cd", "cd src && {c}"),
    ("after assignments", "FOO=1 BAR=two {c}"),
    ("after env", "env {c}"),
    ("after command", "command {c}"),
    ("after exec", "exec {c}"),
    ("after nohup", "nohup {c}"),
    ("after time", "time {c}"),
    ("after timeout", "timeout 60 {c}"),
    ("after timeout with options", "timeout -k 5 --signal=TERM 60 {c}"),
    ("after mamba run", "mamba run -n env {c}"),
    ("after uv run", "uv run {c}"),
    ("after pixi run", "pixi run {c}"),
    ("with a heredoc", "{c} <<'EOF'\nprint(1)\nEOF"),
    ("with /dev/null", "{c} < /dev/null"),
)
REFUSED_SAMPLES = (("python -", DASH), ("python3 -i x.py", INTERACTIVE), ("python -u", NO_SCRIPT))
ALLOWED_SAMPLES = ("python x.py", "python -m pytest -q", "python3 --version", "py -0p")

# Design 8.3 and 13.1: PowerShell (tool PowerShell), read at best effort.
POWERSHELL_REFUSED = (
    ("@'\nprint(1)\n'@ | python -", DASH),
    ("@'\nimport sys\nprint(sys.argv)\n'@ | python3 -", DASH),
    ("@'\nprint(1)\n'@ | python", NO_SCRIPT),
    ("python -", DASH),
    ("python -i x.py", INTERACTIVE),
    ("Get-Content x.py | python", NO_SCRIPT),
)
POWERSHELL_ALLOWED = (
    "python x.py",
    "python -m pytest -q",
    "@'\n{}\n'@ | python -c \"import json,sys; json.load(sys.stdin)\"",
    "Get-Content data.json | python -X utf8 x.py",
    "python --version",
)

# Design 8.3: a command that cannot be split is not checked for R23.
UNPARSED = (
    'python - "unbalanced',
    "python3 -i x.py 'half",
)

# Outside a troy-mode project the hook is silent for every caller (note 1.3).
GATE_COMMANDS = (
    "python -",
    "python3 -i x.py",
    "python",
    "cat x.py | python3",
    "timeout 60 python -",
    "mamba run -n env python -",
    "python - <<'EOF'\nprint(1)\nEOF",
)


class StdinTestCase(HookTestCase):
    """Runs tables of commands for several callers in one project.

    Calls run in parallel, so no test of this kind reads the project's log.
    """

    config = None

    @classmethod
    def setUpClass(cls):
        """Builds one project and starts every role, as hook_helpers convention 10 asks."""
        cls.project = Project() if cls.config is None else Project(config=cls.config)
        cls.addClassCleanup(cls.project.close)
        run_many([start_call(cls.project, c) for c in ROLES])

    def check_refused(self, cases, callers=THREE, tool="Bash", **kwargs):
        """Asserts that each (command, form) is refused with the form and END for each caller."""
        keys = [(caller, command, form) for caller in callers for command, form in cases]
        outs = run_many([bash_call(self.project, caller, command, tool=tool, **kwargs)
                         for caller, command, _ in keys])
        for (caller, command, form), out in zip(keys, outs):
            with self.subTest(caller=caller.label, tool=tool, command=command):
                self.assert_denied(out, form, END, msg=f"{caller.label} {tool} {command!r}:")

    def check_allowed(self, commands, callers=THREE, tool="Bash", **kwargs):
        """Asserts that each command is silent for each caller."""
        keys = [(caller, command) for caller in callers for command in commands]
        outs = run_many([bash_call(self.project, caller, command, tool=tool, **kwargs)
                         for caller, command in keys])
        for (caller, command), out in zip(keys, outs):
            with self.subTest(caller=caller.label, tool=tool, command=command):
                self.assert_silent(out, msg=f"{caller.label} {tool} {command!r}:")


class RefusedFormTests(StdinTestCase):
    """Design 8.3's argument table: each refused form, for every caller."""

    def test_each_refused_form_is_refused(self):
        """Each REFUSED command is refused with its form for the main session, a role, and a subagent.

        The callers are the main session, the Developer, and general-purpose.
        Planted bugs caught: python3 - missed; the -- - form missed; -i inside
        a flag group missed; -W not skipping its value; py -3.13 not skipped
        (py -V:3.13); the main session not checked.
        """
        self.check_refused(REFUSED)

    def test_samples_are_refused_for_every_role_and_other_subagent(self):
        """python -, python3 -i x.py, and a pipe into python are refused for each caller."""
        self.check_refused((("python -", DASH), ("python3 -i x.py", INTERACTIVE),
                            ("cat x.py | python", NO_SCRIPT)), callers=EVERY)

    def test_only_the_first_python_command_names_its_form(self):
        """python -; python -i x.py names python - only, and the reverse names python -i only."""
        outs = run_many([bash_call(self.project, MAIN, "python -; python -i x.py"),
                         bash_call(self.project, MAIN, "python -i x.py && python -")])
        for out, form, other in zip(outs, (DASH, INTERACTIVE), (INTERACTIVE, DASH)):
            with self.subTest(form=form):
                self.assert_denied(out, form, END)
                self.assertNotIn(other, out.reason, out.describe())
                self.assertEqual(1, out.reason.count("R23:"), out.describe())


class AllowedFormTests(StdinTestCase):
    """The note's section 1.5: a script, -c, -m, a version or help flag, or no Python."""

    def test_allowed_forms_pass(self):
        """Each ALLOWED command is silent for the main session, the Developer, and general-purpose."""
        self.check_allowed(ALLOWED)

    def test_command_that_cannot_be_split_is_not_checked(self):
        """An unbalanced quote around python - is silent: design 8.3 does not check it."""
        self.check_allowed(UNPARSED)


class RunnerTests(StdinTestCase):
    """Design 8.3: mamba, micromamba, conda, uv, and pixi run are removed with their options."""

    def test_python_after_a_runner_is_refused(self):
        """Each RUNNER_REFUSED command is refused with its form."""
        self.check_refused(RUNNER_REFUSED)

    def test_scripts_and_modules_after_a_runner_pass(self):
        """Pair: a script, -m, -c, or another program after a runner is silent."""
        self.check_allowed(RUNNER_ALLOWED)


class TimeoutTests(StdinTestCase):
    """Design 7.1 (D223): timeout is a wrapper, with its options and its duration."""

    def test_python_after_timeout_is_refused(self):
        """python -, python3 -i x.py, and python -u after each timeout form are refused.

        Planted bug caught: timeout not unwrapped.
        """
        cases = [(form.replace("{c}", command), name)
                 for form in TIMEOUT_FORMS for command, name in REFUSED_SAMPLES]
        self.check_refused(cases, callers=(MAIN, GP))

    def test_scripts_after_timeout_pass(self):
        """Pair: python x.py and python -m pytest -q after each timeout form are silent."""
        commands = [form.replace("{c}", command) for form in TIMEOUT_FORMS
                    for command in ("python x.py", "python -m pytest -q")]
        self.check_allowed(commands, callers=(MAIN, GP))


class XargsTests(StdinTestCase):
    """Design 7.1 and 8.3: a command that came through xargs gets words from xargs."""

    def test_xargs_python_without_a_script_passes(self):
        """ls *.py | xargs python and find ... | xargs -n 1 python3 are silent.

        Planted bug caught: xargs not exempt.
        """
        self.check_allowed(XARGS_ALLOWED)

    def test_xargs_python_dash_or_i_is_refused(self):
        """Pair: xargs python - and xargs python -i are refused all the same."""
        self.check_refused(XARGS_REFUSED)


class ShellFormTests(StdinTestCase):
    """Design 7.1: refused Python commands are found inside every shell form."""

    def test_refused_samples_inside_every_form(self):
        """python -, python3 -i x.py, and python -u are refused in each form.

        Planted bug caught: timeout not unwrapped (the two timeout forms).
        """
        cases = [(template.replace("{c}", command), form)
                 for _, template in FORMS for command, form in REFUSED_SAMPLES]
        self.check_refused(cases, callers=(MAIN, DEV))

    def test_allowed_samples_inside_every_form(self):
        """Pair: python x.py, python -m pytest -q, python3 --version, and py -0p are silent."""
        commands = [template.replace("{c}", command)
                    for _, template in FORMS for command in ALLOWED_SAMPLES]
        self.check_allowed(commands, callers=(MAIN,))


class PowerShellTests(StdinTestCase):
    """Design 8.3 and 13.1: PowerShell's commands are read the same way."""

    def test_powershell_python_from_standard_input_is_refused(self):
        """@'...'@ | python -, a pipe into python, python -, and python -i are refused."""
        self.check_refused(POWERSHELL_REFUSED, tool="PowerShell")

    def test_powershell_scripts_and_c_pass(self):
        """Pair: python x.py, -m, a here-string into python -c, and --version are silent."""
        self.check_allowed(POWERSHELL_ALLOWED, tool="PowerShell")


class OutsideTroyModeTests(StdinTestCase):
    """Design section 4 and the note's section 1.3: silent outside troy-mode projects."""

    @classmethod
    def setUpClass(cls):
        """Builds a troy-mode project, a git repository without .troy-mode/, and a plain folder."""
        super().setUpClass()
        cls.plain = Project(troy_mode=False)
        cls.addClassCleanup(cls.plain.close)
        cls.folder = plain_folder({"x.py": "print(1)\n"})

    def test_silent_in_a_repository_without_troy_mode(self):
        """Every GATE_COMMANDS command, and PowerShell's here-string, is silent for each caller."""
        keys = [(caller, command, tool) for caller in EVERY
                for command, tool in ([(c, "Bash") for c in GATE_COMMANDS] +
                                      [("@'\nprint(1)\n'@ | python -", "PowerShell")])]
        outs = run_many([bash_call(self.plain, caller, command, tool=tool)
                         for caller, command, tool in keys])
        for (caller, command, tool), out in zip(keys, outs):
            with self.subTest(caller=caller.label, tool=tool, command=command):
                self.assert_silent(out, msg=f"{caller.label} {command!r}:")

    def test_silent_in_a_folder_that_is_no_repository(self):
        """python - from a folder in no git repository is silent for each caller."""
        outs = run_many([bash_call(self.folder, caller, "python -") for caller in THREE])
        for caller, out in zip(THREE, outs):
            with self.subTest(caller=caller.label):
                self.assert_silent(out, msg=caller.label)

    def test_the_same_commands_are_refused_in_troy_mode(self):
        """Pair: the same commands in a troy-mode project are refused for the same callers."""
        self.check_refused((
            ("python -", DASH), ("python3 -i x.py", INTERACTIVE), ("python", NO_SCRIPT),
            ("cat x.py | python3", NO_SCRIPT), ("timeout 60 python -", DASH),
            ("mamba run -n env python -", DASH), ("python - <<'EOF'\nprint(1)\nEOF", DASH)))
        self.check_refused((("@'\nprint(1)\n'@ | python -", DASH),), tool="PowerShell")


class ReasonTests(HookTestCase):
    """Design 8.3 "The refusal" and the note's section 1.1: the whole R23 reason."""

    COMMANDS = (("python -", DASH), ("C:/Python313/python.exe -i x.py", INTERACTIVE),
                ("py -3.13", NO_SCRIPT), ("cat x.py | python3", NO_SCRIPT))

    @classmethod
    def setUpClass(cls):
        """Builds a project with no [lang] environment and one with it."""
        cls.plain = Project()
        cls.env = Project(config=ENV_CONFIG)
        for project in (cls.plain, cls.env):
            cls.addClassCleanup(project.close)
            run_many([start_call(project, DEV)])

    def check_reasons(self, project, pad, env, callers=THREE):
        """Asserts the whole reason for each command and caller.

        Args:
            project: The project to run in.
            pad: ``scratchpad_dir`` as given in the input, or None to leave it out.
            env: The environment the reason must name, or None.
            callers: Who makes the calls.
        """
        keys = [(caller, command, form) for caller in callers for command, form in self.COMMANDS]
        outs = run_many([bash_call(project, caller, command, scratchpad=pad)
                         for caller, command, _ in keys])
        for (caller, command, form), out in zip(keys, outs):
            with self.subTest(caller=caller.label, command=command, pad=pad, env=env):
                self.assert_denied(out, full_reason(form, pad, env), msg=command)
                if pad is None:
                    self.assertNotIn("in the scratchpad (", out.reason, out.describe())
                if env is None:
                    self.assertNotIn("`[lang] environment`", out.reason, out.describe())

    def test_without_scratchpad_or_environment(self):
        """No scratchpad_dir and no [lang] environment: both parts in parentheses are left out."""
        self.check_reasons(self.plain, None, None)

    def test_with_scratchpad(self):
        """scratchpad_dir in the input: the reason names it as given, with / or \\ as it came."""
        self.check_reasons(self.plain, PAD, None)
        self.check_reasons(self.plain, PAD.as_posix(), None, callers=(MAIN,))

    def test_with_environment(self):
        """[lang] environment in the committed config: the reason names it."""
        self.check_reasons(self.env, None, ENV_NAME)

    def test_with_scratchpad_and_environment(self):
        """Both known: the reason names the scratchpad and the environment."""
        self.check_reasons(self.env, PAD, ENV_NAME)

    def test_a_scratchpad_that_does_not_exist_is_named_as_given(self):
        """A scratchpad_dir that does not exist is still named, as given."""
        self.check_reasons(self.plain, SCRATCH / "pad-never-made", None, callers=(MAIN,))

    def test_uncommitted_environment_is_not_read(self):
        """An environment set only in the working tree's config is not named (config at HEAD)."""
        project = Project()
        self.addCleanup(project.close)
        project.write(".troy-mode/config.toml",
                      make_config(extra='[lang]\nenvironment = "uncommitted-env"\n'))
        out = bash_call(project, MAIN, "python -").run()
        self.assert_denied(out, full_reason(DASH))
        self.assertNotIn("uncommitted-env", out.reason, out.describe())


class InvalidConfigTests(HookTestCase):
    """Design 8.3 and the note's section 1.1: an invalid committed config only drops the environment."""

    @classmethod
    def setUpClass(cls):
        """Builds a project whose committed config is invalid."""
        cls.project = Project(config=INVALID_CONFIG)
        cls.addClassCleanup(cls.project.close)
        start_call(cls.project, DEV).run()

    def test_still_refused_with_r23_for_every_caller(self):
        """python -, python -i, and python with no script: the R23 reason, rule python-stdin, no error."""
        for caller in THREE:
            for command, form, pad in (("python -", DASH, None),
                                       ("python3 -i x.py", INTERACTIVE, PAD),
                                       ("cat x.py | python", NO_SCRIPT, None)):
                with self.subTest(caller=caller.label, command=command):
                    before = len(self.project.log_lines())
                    out = bash_call(self.project, caller, command, scratchpad=pad).run()
                    self.assert_denied(out, full_reason(form, pad), msg=command)
                    self.assertFalse(out.reason.startswith(ERROR_PREFIX), out.describe())
                    lines = self.project.log_lines()[before:]
                    self.assertEqual(1, len(lines), f"expected one new log line: {lines}")
                    self.assertEqual(("python-stdin", "deny"),
                                     (lines[0].get("rule"), lines[0].get("decision")))


class LogTests(HookTestCase):
    """Design 8.3 and 10 and the note's section 1.2: one line, rule python-stdin, no command text."""

    def setUp(self):
        """Builds a fresh project so each test sees only its own log lines."""
        self.project = Project()
        self.addCleanup(self.project.close)
        start_call(self.project, DEV).run()

    def test_refusal_logs_rule_python_stdin_without_the_command(self):
        """Each refusal adds one line: python-stdin, deny, no subcommand, no paths, no command text.

        Planted bug caught: the log line holding command text.
        """
        cases = (
            (MAIN, "Bash", f"python - <<'EOF'\nprint('{MARKER}')\nEOF"),
            (DEV, "Bash", f"cd {MARKER} && python3 -i x.py"),
            (GP, "Bash", f"echo {MARKER} | python"),
            (EXPLORE, "Bash", f"timeout 60 python -X {MARKER} -"),
            (MAIN, "PowerShell", f"@'\nprint(\"{MARKER}\")\n'@ | python -"),
        )
        for caller, tool, command in cases:
            with self.subTest(caller=caller.label, tool=tool, command=command):
                before = len(self.project.log_lines())
                out = bash_call(self.project, caller, command, tool=tool).run()
                self.assert_denied(out, "R23:", END, msg=command)
                lines = self.project.log_lines()
                self.assertEqual(before + 1, len(lines), f"expected one new log line: {lines}")
                line = lines[-1]
                self.assertEqual(LOG_KEYS, set(line), f"log keys: {line}")
                self.assertRegex(line["time"], LOG_TIME)
                self.assertIn(line["rule"], LOG_RULES)
                self.assertEqual({"session": SESSION, "agent_id": caller.agent_id,
                                  "agent_type": caller.agent_type, "event": "PreToolUse",
                                  "tool": tool, "rule": "python-stdin", "paths": [],
                                  "subcommand": None, "decision": "deny"},
                                 {k: v for k, v in line.items() if k != "time"})
        text = self.project.log_text()
        self.assertEqual(len(cases), len(self.project.log_lines()), text)
        for fragment in (MARKER, "print(", "x.py", "python -", "python3", "timeout", "<<"):
            self.assertNotIn(fragment, text, f"the log holds {fragment!r}:\n{text}")

    def test_allowed_calls_write_no_line(self):
        """Pair: silent Python calls add no log line."""
        for caller, command in ((MAIN, f"python {MARKER}.py"), (DEV, "python -m pytest -q"),
                                (GP, "echo '{}' | python -c 'import sys'")):
            with self.subTest(caller=caller.label, command=command):
                self.assert_silent(bash_call(self.project, caller, command).run(), msg=command)
        self.assertEqual([], self.project.log_lines())


class MixedLineTests(HookTestCase):
    """The note's section 1.1: a refused git or gh command and a refused Python command."""

    def setUp(self):
        """Builds a fresh project and starts the Developer."""
        self.project = Project()
        self.addCleanup(self.project.close)
        start_call(self.project, DEV).run()

    def run_one(self, caller, command):
        """Runs one call and returns it with the log lines it added."""
        before = len(self.project.log_lines())
        out = bash_call(self.project, caller, command).run()
        return out, self.project.log_lines()[before:]

    def test_git_commit_then_python_names_both_in_line_order(self):
        """A Developer's git commit && python -: both reasons, git first, R23 once; rule git."""
        out, lines = self.run_one(DEV, "git commit -m x && python -")
        self.assert_denied(out, "git commit", DASH, END)
        reason = out.reason
        self.assertEqual(1, reason.count("R23:"), out.describe())
        self.assertLess(reason.index("git commit"), reason.index("R23:"), out.describe())
        self.assertEqual(1, len(lines), f"expected one new log line: {lines}")
        self.assertEqual("git", lines[0].get("rule"), lines)

    def test_python_then_git_push_names_both_in_line_order(self):
        """python -; git push from general-purpose: both reasons, R23 first; rule python-stdin."""
        out, lines = self.run_one(GP, "python -; git push origin feature")
        self.assert_denied(out, DASH, END, "git push")
        reason = out.reason
        self.assertEqual(1, reason.count("R23:"), out.describe())
        self.assertLess(reason.index("R23:"), reason.index("git push"), out.describe())
        self.assertEqual(1, len(lines), f"expected one new log line: {lines}")
        self.assertEqual("python-stdin", lines[0].get("rule"), lines)

    def test_gh_comment_then_python_names_both(self):
        """A Developer's gh pr comment, then python3 -i x.py: both reasons, gh first."""
        out, lines = self.run_one(DEV, "gh pr comment 1 --body ok; python3 -i x.py")
        self.assert_denied(out, "gh pr comment", INTERACTIVE, END)
        reason = out.reason
        self.assertEqual(1, reason.count("R23:"), out.describe())
        self.assertLess(reason.index("gh pr comment"), reason.index("R23:"), out.describe())
        self.assertEqual(1, len(lines), f"expected one new log line: {lines}")
        self.assertEqual("gh", lines[0].get("rule"), lines)

    def test_main_session_commit_and_python_names_only_r23(self):
        """Pair: the main session may commit, so git commit && python - is refused for R23 only."""
        out, lines = self.run_one(MAIN, "git commit -m x && python -")
        self.assert_denied(out, full_reason(DASH))
        self.assertNotIn("git commit", out.reason, out.describe())
        self.assertEqual(1, len(lines), f"expected one new log line: {lines}")
        self.assertEqual("python-stdin", lines[0].get("rule"), lines)


class TimeoutGitTests(HookTestCase):
    """Design 7.1 (D223): the git checks of 7.2 and the guards of 8.2 see through timeout."""

    @classmethod
    def setUpClass(cls):
        """Builds one project and starts the Developer."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        start_call(cls.project, DEV).run()

    def test_git_writes_after_timeout_are_refused_for_subagents(self):
        """timeout 60 git push and timeout -k 5 60 git commit are refused, rule git.

        Planted bug caught: timeout not unwrapped.
        """
        for caller, command, fragment in (
                (DEV, "timeout 60 git push", "git push"),
                (GP, "timeout 60 git push origin feature", "git push"),
                (DEV, "timeout -k 5 60 git commit -m x", "git commit"),
                (GP, "timeout --signal=TERM 30 gh pr comment 1 --body ok", "gh pr comment")):
            with self.subTest(caller=caller.label, command=command):
                before = len(self.project.log_lines())
                out = bash_call(self.project, caller, command).run()
                self.assert_denied(out, fragment, msg=command)
                lines = self.project.log_lines()[before:]
                self.assertEqual(1, len(lines), f"expected one new log line: {lines}")
                self.assertEqual((fragment.split()[0], fragment),
                                 (lines[0].get("rule"), lines[0].get("subcommand")))

    def test_main_session_no_verify_after_timeout_is_refused(self):
        """The main session's timeout 60 git commit --no-verify is refused, rule no-verify."""
        before = len(self.project.log_lines())
        out = bash_call(self.project, MAIN, "timeout 60 git commit --no-verify -m x").run()
        self.assert_denied(out)
        lines = self.project.log_lines()[before:]
        self.assertEqual(1, len(lines), f"expected one new log line: {lines}")
        self.assertEqual("no-verify", lines[0].get("rule"), lines)

    def test_reads_after_timeout_pass(self):
        """Pair: timeout 60 git status for the Developer and timeout 60 git commit for the main session."""
        for caller, command in ((DEV, "timeout 60 git status"), (GP, "timeout 60 gh pr view 1"),
                                (MAIN, "timeout 60 git commit -m x")):
            with self.subTest(caller=caller.label, command=command):
                self.assert_silent(bash_call(self.project, caller, command).run(), msg=command)


if __name__ == "__main__":
    unittest.main()
