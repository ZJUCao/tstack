Role: Code Reviewer
Task: CR1, F04, [F04 4/6 tests] Recipe files
Result: changes-requested
Changed files: None
Checks: see Findings
Summary: The 58 tests follow the approved plan, and every expected value agrees with the design, the example data, and a scratch model of design 1.0, against which 269 tests pass and 2 are skipped; the order cases and the line numbers of F04-T34 included. Each test fails against the mock for the intended reason, and no other test passes against it. ruff and mypy pass, the security review found nothing, and all 26 message texts and 9 places of `f04_support.py` equal the design's. Every escape equals the plan's, except the one in finding 1. The Linux paths of F04-T12, T36, T51, T52, and T53 fit the plan, read but not run.
Findings:
1. Test plan F04-T07 and design 2.4: tests/test_f04_recipe_ids.py:46. The literal `"a\b"` is U+0008 BACKSPACE, a control character the case already covers, so the backslash separator is never tested, and a model passes either way. Write `"a\b"`.
2. Test plan conventions (not blocking): tests/test_f04_read_recipes.py:59. F04-T44's run with `None` compares `Problem.file` as a `Path`, which ignores case on Windows. Unpack the result and call `check_problems` with `recipes == ()`. The same pattern at tests/test_f04_integration.py:239 is fine, because each file is also checked by `str` there.
3. Robustness (not blocking): tests/test_f04_list_toml_files.py:157-159. F04-T53's Windows reason is the English text of WinError 123, so it fails on a Windows in another display language, as the plan notes. A later plan revision could take the reason from the `strerror` of a real `os.listdir` call.
4. Python versions (not blocking, nothing to change now): tests/test_f04_read_whole_file.py:154-157. F04-T34 case 4 depends on TOML 1.0 forbidding an inline table over two lines; a later `tomllib` may read TOML 1.1. F03's tests share this assumption.
5. Platform (not blocking, no change): tests/f04_support.py:421-442. As root on Linux, `listing_denied`'s own `pytest.raises(PermissionError)` fails, so F04-T36 and T52 would fail rather than skip. CI runs as `runner`.
6. Clarity (optional): tests/f04_support.py:421-442. Name the bare constants of `_winapi.CreateFile` (`0x80000000` as `GENERIC_READ`, `0x02000000` as `FILE_FLAG_BACKUP_SEMANTICS`).
7. Reuse (optional): tests/f04_support.py:75-84 and 176. `write` and `put_bytes` copy tests/f03_support.py:65 and 71, and `ZH_EN_KEYS` equals F03's `TAG_KEYS`; import them from `f03_support`.
8. Consistency (optional): tests/test_f04_read_notes_steps.py:48. `with_note` has no return annotation, and its docstring says "holding a note" though it accepts `None`. The two `len(...) ==` asserts in `check_lines` (tests/f04_support.py:408 and 411) repeat what `zip(..., strict=True)` checks.
Question: None
