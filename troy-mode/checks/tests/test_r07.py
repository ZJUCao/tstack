"""Tests for R07: module dependencies (F03 design section 7)."""

import unittest

from prefetch import PrefetchedCase
from shape_builders import CORE, STD_MODS, STORE, UI, Mod, arch_doc, std_base
from shape_runs import IMPL, TESTS, has_detail, run_py


def run_arch(changes, extra=None, mods=STD_MODS, title=IMPL, roots=None, name="python", drop=()):
    """Runs ``code`` on the three-module project with some changes.

    Args:
        changes: Paths mapped to new content for the PR commit.
        extra: Files added to the base commit.
        mods: Rows of the architecture table in the base commit.
        title: PR title.
        roots: Value of ``[lang] source_roots``, or None for the default.
        name: Value of ``[lang] name``.
        drop: Paths of the standard base files to leave out.

    Returns:
        The outcome of the run.
    """
    base = {k: v for k, v in std_base(mods).items() if k not in drop}
    base.update(extra or {})
    return run_py(changes, base, title, name=name, roots=roots)


class DirectionTests(PrefetchedCase):
    """Covers allowed directions and external interfaces."""

    def test_allowed_import_of_an_interface_passes(self):
        """ui may depend on store, and store/api.py is an interface."""
        forms = ["from store.api import get\n", "import store.api\n", "import store.api as s\n",
                 "from store import api\n"]
        for text in forms:
            with self.subTest(text=text):
                out = run_arch({"ui/main.py": text})
                self.assert_rule(out, "R07", "pass")
                self.assert_exit(out, 0)

    def test_undeclared_direction_fails_with_path_and_line(self):
        """core may not depend on store."""
        out = run_arch({"core/x.py": "X = 1\nfrom store.api import get\n"})
        self.assert_rule(out, "R07", "fail")
        self.assert_exit(out, 1)
        self.assertTrue(has_detail(out, "R07", "core/x.py", 2), out.describe())

    def test_dependencies_are_not_transitive(self):
        """ui depends on store and store on core, but ui may not import core."""
        out = run_arch({"ui/main.py": "from core.api import X\n"})
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", "ui/main.py", 1))

    def test_importing_an_internal_file_fails(self):
        """The direction is fine but store/internal.py is not an interface."""
        forms = ["from store.internal import x\n", "import store.internal\n",
                 "from store import internal\n"]
        for text in forms:
            with self.subTest(text=text):
                out = run_arch({"ui/main.py": text})
                self.assert_rule(out, "R07", "fail")
                self.assertTrue(has_detail(out, "R07", "ui/main.py", 1))

    def test_imports_inside_one_module_are_free(self):
        """A module may import its own internals."""
        out = run_arch({"store/a.py": "from store.internal import x\nimport store.api\n"})
        self.assert_rule(out, "R07", "pass")

    def test_third_party_and_missing_imports_are_ignored(self):
        """Imports that resolve to no repository file are third-party."""
        text = "import os\nimport requests\nfrom yaml import safe_load\nfrom core.gone import x\n"
        out = run_arch({"ui/main.py": text})
        self.assert_rule(out, "R07", "pass")

    def test_files_in_no_module_are_never_importers(self):
        """Tests and scripts may import anything."""
        text = "from store.internal import x\nfrom core.internal import y\n"
        out = run_arch({"tests/test_x.py": text, "scripts/run.py": text}, title=TESTS)
        self.assert_rule(out, "R07", "pass")

    def test_target_in_no_module_is_not_checked(self):
        """Importing a script that belongs to no module is not a violation."""
        out = run_arch({"ui/main.py": "from scripts.helper import H\n"})
        self.assert_rule(out, "R07", "pass")

    def test_import_inside_a_function_is_checked(self):
        """Imports are read with ast, wherever they are."""
        text = 'def f():\n    """Doc."""\n    from store.internal import x\n'
        out = run_arch({"ui/main.py": text})
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", "ui/main.py", 3))

    def test_every_violation_is_listed(self):
        """Two files with a bad import are both named."""
        out = run_arch({"core/a.py": "from store.api import x\n",
                        "ui/b.py": "from core.api import y\n", "ui/ok.py": "X = 1\n"})
        self.assertTrue(has_detail(out, "R07", "core/a.py", 1))
        self.assertTrue(has_detail(out, "R07", "ui/b.py", 1))
        self.assertFalse(has_detail(out, "R07", "ui/ok.py"))


class ChangedFileTests(PrefetchedCase):
    """Covers which importers are checked."""

    BAD = "X = 1\nfrom core.api import API\n"

    def test_unchanged_importer_is_not_checked(self):
        """An old bad import passes when its file is not in the PR."""
        out = run_arch({"ui/other.py": "Y = 1\n"}, {"ui/old.py": self.BAD})
        self.assert_rule(out, "R07", "pass")
        self.assert_exit(out, 0)

    def test_old_bad_import_in_a_changed_file_fails(self):
        """R07 checks every import of a changed file, not only changed lines."""
        out = run_arch({"ui/old.py": self.BAD.replace("X = 1", "X = 2")}, {"ui/old.py": self.BAD})
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", "ui/old.py", 2))

    def test_deleted_importer_is_not_checked(self):
        """Deleting the file with the bad import passes."""
        out = run_arch({"ui/old.py": None, "ui/new.py": "Y = 1\n"}, {"ui/old.py": self.BAD})
        self.assert_rule(out, "R07", "pass")

    def test_target_added_in_the_pr_is_resolved_at_the_head(self):
        """An import of a file the PR adds is checked against its module."""
        out = run_arch({"store/fresh.py": "Z = 1\n", "ui/main.py": "import store.fresh\n"})
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", "ui/main.py", 1))

    def test_target_deleted_in_the_pr_is_third_party(self):
        """An import of a file that is gone at the head is ignored."""
        out = run_arch({"store/gone.py": None, "ui/main.py": "import store.gone\n"},
                       {"store/gone.py": "G = 1\n"})
        self.assert_rule(out, "R07", "pass")


class ResolutionTests(PrefetchedCase):
    """Covers how imports map to files."""

    def test_relative_imports_resolve_from_the_importers_folder(self):
        """Same-module relative imports pass."""
        for text in ("from . import internal\n", "from .internal import X\n", "from . import api\n"):
            with self.subTest(text=text):
                out = run_arch({"store/a.py": text})
                self.assert_rule(out, "R07", "pass")

    def test_relative_import_into_another_module_is_checked(self):
        """``..store`` from ui/ is the store folder: interface passes, internals fail."""
        good = run_arch({"ui/main.py": "from ..store import api\n"})
        bad = run_arch({"ui/main.py": "from ..store import internal\n"})
        worse = run_arch({"ui/main.py": "from ..store.internal import X\n"})
        self.assert_rule(good, "R07", "pass")
        self.assert_rule(bad, "R07", "fail")
        self.assert_rule(worse, "R07", "fail")
        self.assertTrue(has_detail(bad, "R07", "ui/main.py", 1))

    def test_relative_imports_climb_one_folder_per_extra_dot(self):
        """In src/app/ui/main.py, ``..store`` is src/app/store, not src/store."""
        mods = [Mod(m.name, [f"src/app/{p}" for p in m.owns], [f"src/app/{p}" for p in m.ext],
                    m.deps) for m in STD_MODS]
        base = {"docs/architecture.md": arch_doc(mods)}
        for name in ("core", "store", "ui"):
            base[f"src/app/{name}/api.py"] = "API = 1\n"
            base[f"src/app/{name}/internal.py"] = "INTERNAL = 1\n"
        cases = [("from ..store import internal\n", "fail"),
                 ("from ..store import api\n", "pass"),
                 ("from ..core import api\n", "fail")]
        for text, expected in cases:
            with self.subTest(text=text):
                out = run_py({"src/app/ui/main.py": text}, base)
                self.assert_rule(out, "R07", expected)

    def test_source_roots_are_used_to_resolve_absolute_imports(self):
        """With source_roots = [src] the import reaches src/store/api.py."""
        mods = [Mod(m.name, [f"src/{p}" for p in m.owns], [f"src/{p}" for p in m.ext], m.deps)
                for m in STD_MODS]
        base = {"docs/architecture.md": arch_doc(mods), "src/store/api.py": "A = 1\n",
                "src/store/internal.py": "I = 1\n", "src/core/api.py": "A = 1\n"}
        change = {"src/core/x.py": "from store.api import A\n"}
        rooted = run_py(change, base, roots=["src"])
        default = run_py(change, base)
        self.assert_rule(rooted, "R07", "fail")
        self.assertTrue(has_detail(rooted, "R07", "src/core/x.py", 1))
        self.assert_rule(default, "R07", "pass")

    def test_from_import_prefers_the_submodule_file(self):
        """``from store.api import get`` tries store/api/get.py before store/api.py."""
        extra = {"store/api/get.py": "G = 1\n"}
        out = run_arch({"ui/main.py": "from store.api import get\n"}, extra)
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", "ui/main.py", 1))

    def test_from_import_falls_back_to_the_module_file(self):
        """With no submodule, the name is an attribute of store/api.py."""
        out = run_arch({"ui/main.py": "from store.api import get\n"})
        self.assert_rule(out, "R07", "pass")

    def test_package_init_is_a_target(self):
        """Packages resolve to __init__.py, which can be the interface."""
        stores = Mod("store", ["store/**"], ["store/api/__init__.py"], ["core"])
        mods = (CORE, stores, UI)
        extra = {"store/api/__init__.py": "A = 1\n"}
        for text in ("import store.api\n", "from store import api\n", "from store.api import A\n"):
            with self.subTest(text=text):
                out = run_arch({"ui/main.py": text}, extra, mods, drop=("store/api.py",))
                self.assert_rule(out, "R07", "pass")

    def test_import_of_a_package_resolves_to_its_init(self):
        """``import store`` reaches store/__init__.py, so it must be an interface."""
        extra = {"store/__init__.py": "S = 1\n"}
        out = run_arch({"ui/main.py": "import store\n"}, extra)
        self.assert_rule(out, "R07", "fail")
        opened = (CORE, Mod("store", ["store/**"], ["store/__init__.py"], ["core"]), UI)
        ok = run_arch({"ui/main.py": "import store\n"}, extra, opened)
        self.assert_rule(ok, "R07", "pass")

    def test_star_matches_within_one_folder_only(self):
        """An interface pattern ``store/pub/*.py`` does not reach deeper files."""
        pub = Mod("store", ["store/**"], ["store/pub/*.py"], ["core"])
        extra = {"store/pub/x.py": "X = 1\n", "store/pub/sub/y.py": "Y = 1\n"}
        near = run_arch({"ui/main.py": "import store.pub.x\n"}, extra, (CORE, pub, UI))
        deep = run_arch({"ui/main.py": "import store.pub.sub.y\n"}, extra, (CORE, pub, UI))
        self.assert_rule(near, "R07", "pass")
        self.assert_rule(deep, "R07", "fail")


class MapTests(PrefetchedCase):
    """Covers reading the module map."""

    BAD = {"ui/main.py": "from core.api import API\n"}

    def test_without_architecture_file_r07_is_skipped(self):
        """No docs/architecture.md means skip."""
        out = run_arch(self.BAD, drop=("docs/architecture.md",))
        self.assert_rule(out, "R07", "skip")
        self.assert_exit(out, 0)

    def test_architecture_file_without_a_table_is_skipped(self):
        """A document with no module table means skip."""
        extra = {"docs/architecture.md": "# Architecture\n\n## 3. Modules\n\nNone yet.\n"}
        self.assert_rule(run_arch(self.BAD, extra), "R07", "skip")

    def test_table_under_another_heading_is_not_the_map(self):
        """Only the table under the ``## 3.`` heading is read."""
        extra = {"docs/architecture.md": arch_doc(STD_MODS, heading="## 2. Context")}
        self.assert_rule(run_arch(self.BAD, extra), "R07", "skip")

    def test_without_a_language_r07_is_skipped(self):
        """No [lang] name means skip even with a map."""
        self.assert_rule(run_arch(self.BAD, name=None), "R07", "skip")

    def test_cpp_language_runs_r07_with_the_cpp_adapter(self):
        """With name = cpp an include of another module's header is judged."""
        extra = {"core/api.h": "#pragma once\n"}
        text = '#include "../core/api.h"\n'
        out = run_arch({"ui/main.cpp": text}, extra, name="cpp")
        self.assert_rule(out, "R07", "fail")
        self.assertTrue(has_detail(out, "R07", "ui/main.cpp", 1), out.describe())

    def test_columns_are_found_by_header_name(self):
        """Column order and extra columns do not matter."""
        cols = ("Module", "May depend on", "External interfaces", "Owns")
        extra = {"docs/architecture.md": arch_doc(STD_MODS, columns=cols, notes=True)}
        good = run_arch({"ui/main.py": "from store.api import get\n"}, extra)
        bad = run_arch(self.BAD, extra)
        self.assert_rule(good, "R07", "pass")
        self.assert_rule(bad, "R07", "fail")

    def test_several_patterns_in_one_cell_are_all_used(self):
        """Every backticked string of a cell is a pattern."""
        store = Mod("store", ["store/**", "extra/**"], ["store/api.py", "store/types.py"], ["core"])
        extra = {"store/types.py": "T = 1\n", "extra/e.py": "E = 1\n"}
        mods = (CORE, store, UI)
        for text, expected in (("import store.types\n", "pass"), ("import extra.e\n", "fail")):
            with self.subTest(text=text):
                out = run_arch({"ui/main.py": text}, extra, mods)
                self.assert_rule(out, "R07", expected)

    def test_map_is_read_from_the_merge_base(self):
        """A PR that edits the table does not change its own rules."""
        loose = (Mod("core", ["core/**"], ["core/api.py"], ["store"]), STORE, UI)
        changes = {"docs/architecture.md": arch_doc(loose), **{"core/x.py": "import store.api\n"}}
        out = run_arch(changes)
        self.assert_rule(out, "R07", "fail")

    def test_map_added_by_the_pr_is_not_used(self):
        """With no map at the merge base R07 is skipped."""
        changes = {"docs/architecture.md": arch_doc(STD_MODS), **self.BAD}
        out = run_arch(changes, drop=("docs/architecture.md",))
        self.assert_rule(out, "R07", "skip")


class GraphTests(PrefetchedCase):
    """Covers cycles and unknown modules."""

    PLAIN = {"src/note.py": "X = 1\n"}

    def test_declared_cycle_fails(self):
        """core and store that depend on each other form a cycle."""
        mods = (Mod("core", ["core/**"], ["core/api.py"], ["store"]), STORE, UI)
        out = run_arch(self.PLAIN, mods=mods)
        self.assert_rule(out, "R07", "fail")
        self.assert_exit(out, 1)

    def test_declared_three_module_cycle_fails(self):
        """A cycle through three modules fails."""
        mods = (Mod("core", ["core/**"], ["core/api.py"], ["ui"]), STORE, UI)
        self.assert_rule(run_arch(self.PLAIN, mods=mods), "R07", "fail")

    def test_acyclic_declaration_passes(self):
        """The standard chain ui, store, core has no cycle."""
        out = run_arch(self.PLAIN)
        self.assert_rule(out, "R07", "pass")
        self.assert_exit(out, 0)

    def test_unknown_module_in_may_depend_on_fails(self):
        """May depend on must name modules of the table."""
        mods = (CORE, STORE, Mod("ui", ["ui/**"], ["ui/api.py"], ["store", "ghost"]))
        out = run_arch(self.PLAIN, mods=mods)
        self.assert_rule(out, "R07", "fail")
        self.assert_exit(out, 1)

    def test_import_cycle_through_a_changed_file_fails(self):
        """An old file closes a cycle that a changed import completes."""
        mods = (Mod("core", ["core/**"], ["core/api.py"], ["store"]),
                Mod("store", ["store/**"], ["store/api.py"]), UI)
        extra = {"store/old.py": "from core.api import API\n"}
        out = run_arch({"core/x.py": "from store.api import API\n"}, extra, mods)
        self.assert_rule(out, "R07", "fail")
        self.assert_exit(out, 1)

    def test_import_cycle_with_no_changed_import_is_ignored(self):
        """The same cycle passes when no changed file takes part in it."""
        mods = (Mod("core", ["core/**"], ["core/api.py"], ["store"]),
                Mod("store", ["store/**"], ["store/api.py"]), UI)
        extra = {"store/old.py": "from core.api import API\n",
                 "core/x.py": "from store.api import API\n"}
        out = run_arch({"core/other.py": "Y = 1\n"}, extra, mods)
        self.assert_rule(out, "R07", "pass")


if __name__ == "__main__":
    unittest.main()
