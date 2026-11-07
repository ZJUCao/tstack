"""The project's CI workflow with the language pack's job (design 5.2, 5.3, and 6)."""

import re

_JOBS = re.compile(r"^jobs:[ \t]*$", re.MULTILINE)
_TOP_LEVEL_KEY = re.compile(r"^[^\s#][^\n]*:", re.MULTILINE)
_CODE_JOB = re.compile(r"^[ \t]+troy-code:[ \t]*$", re.MULTILINE)


def workflow_problems(text: str) -> list[str]:
    """Checks that the pack's job can go under the workflow's jobs: key.

    Args:
        text: The workflow's text.

    Returns:
        One message per problem, empty when the job can be added.
    """
    jobs = _JOBS.search(text)
    if not jobs:
        return ["has no top-level jobs: key."]
    problems = []
    later = _TOP_LEVEL_KEY.search(text, jobs.end())
    if later:
        problems.append(f"has the top-level key {later.group(0)} after jobs:, so the pack's "
                        "job cannot be added at the end.")
    if _CODE_JOB.search(text):
        problems.append("already has a troy-code job.")
    return problems


def append_job(workflow: str, job: str) -> str:
    """Adds the pack's job at the end of the workflow, under jobs:.

    Args:
        workflow: The workflow's text, whose last top-level key is jobs:.
        job: The pack's workflow-job.yml, whose job is indented under jobs:.

    Returns:
        The workflow with the job after its existing jobs.
    """
    return workflow.rstrip("\n") + "\n\n" + job
