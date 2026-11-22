<!--
Planted bugs of F16 design 14.2, and the tests that catch each one.

Plant each bug alone in a scratch copy, run
    python -m unittest discover -s troy-mode/exam/tests
(and, for bug 9, python -m unittest discover -s troy-mode/dev/tests), and
count the failures. Test names are module.Class.method.

1. The judge's folder holding the key.
   test_exam_cli.MainExamTests.test_judge_folder_holds_only_rubric_and_outputs
   test_exam_blinding.JudgeFolderTests.test_only_the_rubric_and_the_outputs
     (when the key is written by build_folder)

2. A label that names its version.
   test_exam_blinding.LabelTests.test_labels_are_r_numbers_that_name_nothing
   test_exam_cli.MainExamTests.test_judge_labels_are_r_numbers
   test_exam_cli.MainExamTests.test_judge_folder_holds_only_rubric_and_outputs

3. A later commit reachable in the case's origin.
   test_exam_project.BuildProjectTests.test_no_later_commit_in_origin
   test_exam_project.BuildProjectTests.test_history_ends_at_the_start
   test_exam_cli.MainExamTests.test_no_later_commit_in_the_run

4. The brief compared without the agent file (affected).
   test_exam_cli.AffectedTests.test_an_agent_file_change_affects_the_case
   test_exam_cli.RoleInputsTests.test_the_agent_file_is_an_input

5. The not-worse rule off by one.
   test_exam_compare.NotWorseTests.test_every_pair_at_five_runs
   test_exam_compare.NotWorseTests.test_every_pair_at_ten_runs
   test_exam_compare.NotWorseTests.test_the_edges
   test_exam_compare.ChanceTests.test_not_worse_chances_match_the_design
   test_exam_compare.ChanceTests.test_not_worse_chances_are_exact

6. The target rule passing at a tie.
   test_exam_compare.TargetTests.test_ties_never_pass
   test_exam_compare.TargetTests.test_every_pair_at_five_runs
   test_exam_compare.TargetTests.test_every_pair_at_ten_runs
   test_exam_compare.ChanceTests.test_target_chances_are_exact

7. The estimate counting the role's cost but not the judge's.
   test_exam_budget.EstimateTests.test_judge_passes_are_counted
   test_exam_budget.EstimateTests.test_cases_add_up
   test_exam_budget.EstimateTests.test_the_designs_one_developer_case
   test_exam_cli.BudgetLineTests.test_exit_2_with_the_estimate_and_no_run
     ($102 holds the $2 judge pass)

8. The budget guard ignoring reused runs.
   test_exam_budget.EstimateTests.test_reused_runs_cost_nothing
   test_exam_budget.EstimateTests.test_reuse_keeps_an_exam_under_the_line
   test_exam_budget.NewRunsTests.test_new_runs

9. check_exam.py accepting a stale hash.
   troy-mode/dev/tests/test_check_exam.py:
   test_check_exam.MainTests.test_a_stale_hash_fails
   test_check_exam.ScriptTests.test_no_arguments_in_the_repository

10. The hash leaving out the templates.
   test_exam_instructions.ListTests.test_instruction_files
   test_exam_instructions.ListTests.test_this_repository
   test_exam_instructions.HashTests.test_each_listed_file_changes_the_hash
     (the troy-mode/templates/ subtests)
   test_exam_instructions.HashTests.test_a_new_template_changes_the_hash
   test_exam_instructions.HashTests.test_a_rename_changes_the_hash
   test_exam_instructions.TreeTests.test_each_commit_has_its_own_content

11. U4 missing "python3 -".
   test_exam_checks.ReadsStdinTests.test_true_cases
     ("python3 - < /dev/null", "git status; python3 - < /dev/null")
   test_exam_checks.U4Tests.test_python3_dash

12. U3 missing a CRLF-to-LF change.
   test_exam_checks.U3Tests.test_crlf_rewritten_as_lf_fails

13. U6 accepting a read after the first change.
   test_exam_checks.U6Tests.test_read_after_the_first_change_fails
   test_exam_checks.U6Tests.test_a_refused_change_is_still_the_first_change
   test_exam_checks.U6Tests.test_notebook_and_multi_edits_are_changes

14. Reuse with a different CLI version.
   test_exam_reuse.ReusableTests.test_each_condition_breaks_reuse_alone (the cli subtest)
   test_exam_reuse.ReusableTests.test_a_newer_cli_is_not_reused
   test_exam_reuse.LogTests.test_rows_read_back_are_reusable

15. The gh stand-in letting "gh pr comment" through.
   test_exam_project.GhStubTests.test_pr_comment_is_refused_and_changes_nothing
   test_exam_cli.MainExamTests.test_the_gh_stand_in_is_first_on_the_path

Planted bugs of design 10.3, the second round (tstack #92).

16. The second round's estimate leaving out the base's runs when its first 5 were reused.
   test_exam_budget.WholeTests.test_the_designs_exam_8
   test_exam_budget.WholeTests.test_the_designs_exam_10
   test_exam_budget.WholeTests.test_reused_base_runs_are_new_in_the_second_round
   test_exam_budget.SecondRoundTests.test_every_run_of_both_versions_is_new
     (when second_round itself leaves them out)
   test_exam_second_round.RoundTests.test_the_second_rounds_estimate_from_each_versions_own_runs
   test_exam_second_round.RoundTests.test_the_guard_holds_the_first_round_and_this_round
   test_exam_second_round.LineTests.test_the_exam_waits_before_the_second_round
   test_exam_second_round.LineTests.test_only_the_asked_round_joins_the_estimate

17. The guard counting every case's second round from the start.
   test_exam_second_round.GuardWaitTests.test_the_exam_waits_after_three_runs
   test_exam_second_round.GuardWaitTests.test_the_saved_state_waits_at_the_guard
   test_exam_second_round.RoundTests.test_the_guard_holds_the_first_round_and_this_round
   test_exam_second_round.LineTests.test_only_the_asked_round_joins_the_estimate
   test_exam_second_round.StartWaitTests.test_resume_yes_starts_it_with_the_whole_approved
   test_exam_second_round.RunYesTests.test_run_yes_approves_the_whole

18. A reused run counted at $0 in its version's median.
   test_exam_second_round.RoundTests.test_the_second_rounds_estimate_from_each_versions_own_runs
   test_exam_second_round.RoundTests.test_the_guard_holds_the_first_round_and_this_round
   test_exam_second_round.LineTests.test_the_exam_waits_before_the_second_round
   test_exam_second_round.LineTests.test_only_the_asked_round_joins_the_estimate

19. The second round's judge pass left out.
   test_exam_budget.SecondRoundTests.test_the_judge_pass_is_counted
   test_exam_budget.SecondRoundTests.test_the_designs_figures_by_own_cost
   test_exam_budget.WholeTests.test_the_designs_exam_8
   test_exam_second_round.RoundTests.test_the_second_rounds_estimate_from_each_versions_own_runs
   test_exam_second_round.RoundTests.test_the_second_rounds_judge_pass_is_in_its_estimate
   test_exam_second_round.LineTests.test_only_the_asked_round_joins_the_estimate
   test_exam_second_round.LineTests.test_the_waiting_report

20. resume going on without --yes (for an exam waiting for Troy).
   test_exam_second_round.LineTests.test_resume_without_a_flag_refuses
   test_exam_second_round.StartWaitTests.test_resume_without_a_flag_refuses

21. A case cut short shown as "worse" (or "not fixed").
   test_exam_second_round.GuardWaitTests.test_the_case_cut_short_has_no_verdict
   test_exam_second_round.StopBeforeStartTests.test_the_target_shows_no_verdict
   test_exam_second_round.RerunsTests.test_the_case_has_no_verdict
     (when the bug is in the path where reruns run out)
-->

# Planted bugs of F16 design 14.2

The list is the comment block at the top of this file; read it in the raw file.
