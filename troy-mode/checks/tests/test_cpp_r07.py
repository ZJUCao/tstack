"""Tests for R07 with the C/C++ adapter: module dependencies (design sections 6 and 7)."""

import unittest

from cpp_builders import CORE, STORE, TESTS, UI, run_arch
from prefetch import PrefetchedCase
from shape_builders import Mod, arch_doc
from shape_runs import has_detail

UI_MAIN = "src/ui/main.cpp"


def inc(path, form='#include "{}"'):
    """Builds one include line, ending in a line feed."""
    return form.format(path) + "\n"


class DirectionTests(PrefetchedCase):
    """Covers allowed directions and external interfaces."""

    def test_allowed_include_of_an_interface_passes_in_every_spelling(self):
        """ui may depend on store, and store/api.h is an interface."""
        forms = [
            '#include "store/api.h"', '#  include "store/api.h"', '# include "store/api.h"',
            '#include   "store/api.h"', '#include "store/api.h"  // reason',
        ]
        for text in forms:
            with self.subTest(text=text):
                out = run_arch({UI_MAIN: text + "\n"})
                self.assert_rule(out, "R07", "pass")
                self.assert_exit(out, 0)

    def test_header_importers_are_checked_like_sources(self):
        """A header that includes across modules is judged too."""
        out = run_arch({"src/core/x.h": inc("store/api.h")})
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", "src/core/x.h", 1), out.describe())

    def test_every_include_spelling_is_judged_when_it_breaks_a_rule(self):
        """The same spellings fail when the target is an internal header."""
        for form in ('#include "{}"', "#  include \"{}\"", '# include "{}"'):
            with self.subTest(form=form):
                out = run_arch({UI_MAIN: inc("store/internal.h", form)})
                self.assert_rule(out, "R07", "fail")
                self.assertTrue(has_detail(out, "R07", UI_MAIN, 1), out.describe())

    def test_undeclared_direction_fails_with_path_and_line(self):
        """core may not depend on store."""
        out = run_arch({"src/core/x.cpp": "int X;\n" + inc("store/api.h")})
        self.assert_rule(out, "R07", "fail")
        self.assert_exit(out, 1)
        self.assertTrue(has_detail(out, "R07", "src/core/x.cpp", 2), out.describe())

    def test_dependencies_are_not_transitive(self):
        """ui depends on store and store on core, but ui may not include core."""
        out = run_arch({UI_MAIN: inc("core/api.h")})
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", UI_MAIN, 1))

    def test_including_an_internal_header_fails(self):
        """The direction is fine but store/internal.h is not an interface."""
        out = run_arch({UI_MAIN: inc("store/internal.h")})
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", UI_MAIN, 1))

    def test_includes_inside_one_module_are_free(self):
        """A module may include its own internals, by its own folder or a path."""
        text = inc("internal.h") + inc("store/internal.h") + inc("api.h")
        out = run_arch({"src/store/a.cpp": text})
        self.assert_rule(out, "R07", "pass")

    def test_parent_folder_paths_are_resolved(self):
        """A ../ path from the including file's folder names the target."""
        out = run_arch({UI_MAIN: inc("../core/api.h")})
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", UI_MAIN, 1))

    def test_every_violation_is_listed(self):
        """Two files with a bad include are both named, a good one is not."""
        out = run_arch({
            "src/core/a.cpp": inc("store/api.h"),
            "src/ui/b.cpp": inc("core/api.h"),
            "src/ui/ok.cpp": "int X;\n",
        })
        self.assertTrue(has_detail(out, "R07", "src/core/a.cpp", 1))
        self.assertTrue(has_detail(out, "R07", "src/ui/b.cpp", 1))
        self.assertFalse(has_detail(out, "R07", "src/ui/ok.cpp"))


class IgnoredIncludeTests(PrefetchedCase):
    """Covers includes that are not imports."""

    def test_angle_bracket_includes_are_external(self):
        """#include <...> is ignored even when the path names a repository file."""
        text = "#include <store/internal.h>\n#include <core/api.h>\n#include <vector>\n"
        out = run_arch({UI_MAIN: text})
        self.assert_rule(out, "R07", "pass")

    def test_includes_in_comments_are_ignored(self):
        """Line and block comments hide an include."""
        text = (
            '// #include "core/api.h"\n//#include "core/api.h"\n'
            '/* #include "core/api.h" */\n'
            '/*\n#include "core/api.h"\n#include "store/internal.h"\n*/\n'
        )
        out = run_arch({UI_MAIN: text})
        self.assert_rule(out, "R07", "pass")
        self.assert_exit(out, 0)

    def test_include_after_a_closed_block_comment_counts(self):
        """The block comment ends, so the next include is real."""
        text = '/* one\n   two */\n#include "core/api.h"\n'
        out = run_arch({UI_MAIN: text})
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", UI_MAIN, 3), out.describe())

    def test_unresolved_includes_are_third_party(self):
        """An include that names no repository file is ignored."""
        text = inc("gone.h") + inc("core/gone.h") + inc("boost/config.hpp")
        out = run_arch({UI_MAIN: text})
        self.assert_rule(out, "R07", "pass")

    def test_files_in_no_module_are_never_importers(self):
        """Tests and tools may include anything."""
        text = inc("store/internal.h") + inc("core/internal.h")
        changes = {"tests/x.cc": text, "src/tools/run.cc": text, "src/a_test.cc": text}
        out = run_arch(changes, title=TESTS)
        self.assert_rule(out, "R07", "pass")

    def test_target_in_no_module_is_not_checked(self):
        """Including a header that belongs to no module is not a violation."""
        out = run_arch({UI_MAIN: inc("tools/helper.h")})
        self.assert_rule(out, "R07", "pass")


class ResolutionTests(PrefetchedCase):
    """Covers where includes are looked for."""

    SHARED = (
        CORE,
        Mod("store", ["src/store/**"], ["src/store/api.h", "src/store/shared.h"], ["core"]),
        UI,
    )
    EXTRA = {"src/core/shared.h": "#pragma once\n", "src/store/shared.h": "#pragma once\n"}

    def test_the_including_files_own_folder_comes_first(self):
        """src/ui/api.h wins over src/core/api.h, so ui stays within itself."""
        out = run_arch({UI_MAIN: inc("api.h")}, include_dirs=["src/core"])
        self.assert_rule(out, "R07", "pass")
        out = run_arch({"src/store/a.cpp": inc("api.h")}, include_dirs=["src/core"])
        self.assert_rule(out, "R07", "pass")

    def test_include_dirs_are_tried_in_order(self):
        """The first folder that holds the file wins."""
        first_core = run_arch({UI_MAIN: inc("shared.h")}, self.EXTRA, self.SHARED,
                              include_dirs=["src/core", "src/store"])
        first_store = run_arch({UI_MAIN: inc("shared.h")}, self.EXTRA, self.SHARED,
                               include_dirs=["src/store", "src/core"])
        self.assert_rule(first_core, "R07", "fail")
        self.assertTrue(has_detail(first_core, "R07", UI_MAIN, 1), first_core.describe())
        self.assert_rule(first_store, "R07", "pass")

    def test_without_include_dirs_only_the_own_folder_is_tried(self):
        """With no include_dirs, src/store/api.h is not found from src/ui."""
        text = inc("store/api.h") + inc("core/api.h")
        without = run_arch({UI_MAIN: text}, include_dirs=None)
        with_dir = run_arch({UI_MAIN: text}, include_dirs=["src"])
        self.assert_rule(without, "R07", "pass")
        self.assert_rule(with_dir, "R07", "fail")
        self.assertTrue(has_detail(with_dir, "R07", UI_MAIN, 2), with_dir.describe())

    def test_a_missing_include_dir_is_skipped(self):
        """A folder that does not exist does not stop the search."""
        out = run_arch({UI_MAIN: inc("core/api.h")}, include_dirs=["nowhere", "src"])
        self.assert_rule(out, "R07", "fail")

    def test_relative_include_without_include_dirs_still_works(self):
        """A path that is right from the including file's folder resolves."""
        out = run_arch({"src/ui/x.cpp": inc("../store/internal.h")}, include_dirs=None)
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", "src/ui/x.cpp", 1))

    def test_header_added_in_the_pr_is_resolved_at_the_head(self):
        """An include of a file the PR adds is checked against its module."""
        changes = {"src/store/fresh.h": "#pragma once\n", UI_MAIN: inc("store/fresh.h")}
        out = run_arch(changes)
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", UI_MAIN, 1))

    def test_header_deleted_in_the_pr_is_not_resolved(self):
        """At the head the file is gone, so the include names no repository file."""
        changes = {"src/store/internal.h": None, UI_MAIN: inc("store/internal.h")}
        out = run_arch(changes)
        self.assert_rule(out, "R07", "pass")


class ChangedFileTests(PrefetchedCase):
    """Covers which importers are checked."""

    BAD = "int X;\n" + inc("core/api.h")

    def test_unchanged_importer_is_not_checked(self):
        """An old bad include passes when its file is not in the PR."""
        out = run_arch({"src/ui/other.cpp": "int Y;\n"}, {"src/ui/old.cpp": self.BAD})
        self.assert_rule(out, "R07", "pass")
        self.assert_exit(out, 0)

    def test_old_bad_include_in_a_changed_file_fails(self):
        """R07 checks every include of a changed file, not only changed lines."""
        changed = self.BAD.replace("int X;", "int Z;")
        out = run_arch({"src/ui/old.cpp": changed}, {"src/ui/old.cpp": self.BAD})
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", "src/ui/old.cpp", 2))

    def test_deleted_importer_is_not_checked(self):
        """Deleting the file with the bad include passes."""
        out = run_arch({"src/ui/old.cpp": None, "src/ui/new.cpp": "int Y;\n"},
                       {"src/ui/old.cpp": self.BAD})
        self.assert_rule(out, "R07", "pass")


class MapTests(PrefetchedCase):
    """Covers reading the module map."""

    BAD = {UI_MAIN: inc("core/api.h")}

    def test_without_architecture_file_r07_is_skipped(self):
        """No docs/architecture.md means skip."""
        out = run_arch(self.BAD, drop=("docs/architecture.md",))
        self.assert_rule(out, "R07", "skip")
        self.assert_exit(out, 0)

    def test_without_a_language_r07_is_skipped(self):
        """No [lang] name means skip, even with a map and a bad include."""
        self.assert_rule(run_arch(self.BAD, name=None), "R07", "skip")

    def test_the_cpp_adapter_runs_r07(self):
        """R07 is no longer skipped for name = cpp."""
        out = run_arch(self.BAD)
        self.assert_rule(out, "R07", "fail")
        self.assert_exit(out, 1)

    def test_map_is_read_from_the_merge_base(self):
        """A PR that edits the table does not change its own rules."""
        loose = (Mod("core", ["src/core/**"], ["src/core/api.h"], ["store"]), STORE, UI)
        changes = {"docs/architecture.md": arch_doc(loose), "src/core/x.cpp": inc("store/api.h")}
        self.assert_rule(run_arch(changes), "R07", "fail")


class GraphTests(PrefetchedCase):
    """Covers cycles and unknown modules."""

    PLAIN = {"src/note.cc": "int X;\n"}
    CORE_ON_STORE = Mod("core", ["src/core/**"], ["src/core/api.h"], ["store"])
    STORE_ALONE = Mod("store", ["src/store/**"], ["src/store/api.h"])

    def test_declared_cycle_fails(self):
        """core and store that depend on each other form a cycle."""
        out = run_arch(self.PLAIN, mods=(self.CORE_ON_STORE, STORE, UI))
        self.assert_rule(out, "R07", "fail")
        self.assert_exit(out, 1)

    def test_declared_three_module_cycle_fails(self):
        """A cycle through three modules fails."""
        core = Mod("core", ["src/core/**"], ["src/core/api.h"], ["ui"])
        self.assert_rule(run_arch(self.PLAIN, mods=(core, STORE, UI)), "R07", "fail")

    def test_acyclic_declaration_passes(self):
        """The standard chain ui, store, core has no cycle."""
        out = run_arch(self.PLAIN)
        self.assert_rule(out, "R07", "pass")
        self.assert_exit(out, 0)

    def test_unknown_module_in_may_depend_on_fails(self):
        """May depend on must name modules of the table."""
        ui = Mod("ui", ["src/ui/**"], ["src/ui/api.h"], ["store", "ghost"])
        out = run_arch(self.PLAIN, mods=(CORE, STORE, ui))
        self.assert_rule(out, "R07", "fail")
        self.assert_exit(out, 1)

    def test_include_cycle_through_a_changed_file_fails(self):
        """An old header closes a cycle that a changed include completes."""
        mods = (self.CORE_ON_STORE, self.STORE_ALONE, UI)
        extra = {"src/store/old.h": inc("core/api.h")}
        out = run_arch({"src/core/x.cpp": inc("store/api.h")}, extra, mods)
        self.assert_rule(out, "R07", "fail")
        self.assert_exit(out, 1)

    def test_include_cycle_with_no_changed_include_is_ignored(self):
        """The same cycle passes when no changed file takes part in it."""
        mods = (self.CORE_ON_STORE, self.STORE_ALONE, UI)
        extra = {"src/store/old.h": inc("core/api.h"), "src/core/x.cpp": inc("store/api.h")}
        out = run_arch({"src/core/other.cpp": "int Y;\n"}, extra, mods)
        self.assert_rule(out, "R07", "pass")


if __name__ == "__main__":
    unittest.main()
