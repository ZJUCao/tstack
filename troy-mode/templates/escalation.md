# Escalation message

<!-- template: The shape of the message troy-mode sends when it stops and asks Troy (troy-mode requirements 5.7). It is a chat message, not a file in the project. Write it in the language Troy uses in the session. -->

```text
Stopped at: {{feature-id}}, stage {{stage}}.
Why: {{trigger}}.
Facts:
- {{side}} says {{position}} ({{link}}).
- {{side}} says {{position}} ({{link}}).
Option A: {{option}}. {{consequences}}.
Option B: {{option}}. {{consequences}}.
Recommendation: {{A or B}}, because {{reason}}.
```

Triggers, from troy-mode requirements 5.7:

- A review loop reached 3 rounds without agreement.
- A change needs the requirements or the architecture to change.
- An implementation still fails its tests after 3 attempts.
- A new third-party dependency is needed.
- An irreversible action falls outside the merge rights.
