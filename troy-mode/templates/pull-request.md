<!--
template: PR title is [<ID> <stage>] <summary>, or [<kind>] <summary> for a PR that belongs to no feature or bug.
  [F04 1/6 design]     documents
  [F04 2/6 test-plan]  documents
  [F04 3/6 mock]       source
  [F04 4/6 tests]      tests
  [F04 5/6 impl]       source
  [F04 6/6 accept]     documents
  [B12 A/B test]       tests
  [B12 B/B fix]        source
  [F04 test-fix]       tests
  [docs]               documents
  [rules]              rules table and check config
  [refactor]           source
Each PR has exactly one commit (R01) and holds one stage's output only (R02).
Remove this comment and every {{marker}} before opening the PR.
-->

## Why

{{goal, in one or two sentences}}

## What

{{the change, with the IDs it covers}}

## Checks

{{what ran and the result}}

## Soft-limit reason

{{why this PR passes R03 or R06, or None}}
