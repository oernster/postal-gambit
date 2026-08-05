# Postal Gambit: Technical Debt

A standing reference to the project's outstanding technical debt. It records what is still open, weighs whether each item is worth doing and gives the rationale. Every item is a behaviour-preserving internal concern: nothing here proposes reverting a feature or changing any UI or UX behaviour. Scope is the whole repository (the `postalgambit` package, the composition root, the bespoke installer, the delivery scripts for Windows, Linux and macOS, plus the GitHub Pages site) read against `ARCHITECTURE.md`, `WIRE_FORMAT.md`, `TESTING.md` and the tests under `tests/structural/`.

This project is in strong shape. Five structural suites (domain purity, layer boundaries, module size, style and a no-network invariant) share one AST scanner, the no-network invariant is proven over everything a user installs rather than over the package alone, the size cap covers the test tree and carries a danger band, the package and the setup program's Qt-free halves are gated at 100% line and branch coverage, `VERSION` is the single source of truth (nothing outside it names the product's version; the version-like literals in `tests/installer/` are fixture data chosen to exercise the upgrade comparison) and there is not a single em dash in the tree. One item remains and it is continuous rather than a task with an end state.

---

## 1. The UI layers are omitted from the gate in full

`[tool.coverage.run]` measures `postalgambit`, `installer.ops` and `installer.state`, with `postalgambit/ui/*` and `version.py` omitted; `installer/ui`, `installer/app.py`, `installer/cli.py` and `installer/shared` are simply outside the source list. The version module is a file read and the UI omissions are the standard portfolio position, correct for painting and layout.

It is recorded so the omission is never read as "the UI has no logic". `main_window.py` is the largest module in the package and a correspondence-chess client's window carries real decisions.

The eligibility questions have moved. `MoveService` now answers which games an action may be offered for at all (`in_progress`, `draw_acceptable`, `awaiting_opponent`) and whether a move promotes a pawn (`is_promotion`, over a `BoardView.piece_at` that owns the square arithmetic its own docstring defines). The window and the action bar ask rather than filtering records themselves, so each question has one answer and every one of them sits inside the gate. That also removed the UI's second copy of the board's coordinate mapping: `main_window.py` no longer imports the widget's `BOARD_SIZE` and `FILES` to work out an index.

What is left in the UI is genuinely presentational, plus the flows that sequence dialogs. The next bite, when someone is next in the file: `GameActions` still decides what a confirmation says and which games it names; `_show_selected` still assembles the window's state from four service calls in a fixed order. Neither is urgent.

---

## Looks like debt, not worth touching

- `builddmg.py` at 367 lines and the other delivery scripts. Linear recipes, exempt from the cap by design.
- `INSTALLER_LICENSE` beside `LICENSE`. The installer wrapper carries an as-is notice distinct from the application licence. Deliberate and load-bearing.
- The fourteen tracked PNGs plus the `.ico` and `.icns`. Emitted by `generate_icons.py` from a single master and consumed by named packaging paths on three platforms.
- `WIRE_FORMAT.md` as a separate document from `ARCHITECTURE.md`. The wire format is a compatibility contract between two installations that may be on different versions; it deserves its own file and its own version discipline.
- `tests/structural/scan.py` being a helper module inside the test tree rather than a package. One scanner shared by five suites is exactly right.
- Twenty-six findings from a default `ruff check`, measured, none of them in the gate this repository actually runs (black and flake8, both asserted in-suite by `test_style.py`). They are import ordering in `main.py`, `Mapping` imported from `typing` rather than `collections.abc`, `timezone.utc` rather than the `datetime.UTC` alias and `subprocess.run` without an explicit `check` in two delivery scripts. Discretionary modernisation rather than debt. Two of them would be actively wrong to accept: `RUF100` calls the `# noqa: N802 (Qt override)` comments on `event()` and `showEvent()` unused, which is true only because no pep8-naming plugin is installed; the comment is what tells the next reader the odd casing is Qt's and not a slip.

## Not debt (do not "fix" these)

These look like candidates but are correct as they stand; changing them would regress or add cost for nothing.

- **`test_no_network.py` itself.** It is the mechanism that makes "the app never touches the network" a fact rather than a marketing line; it is the single best-targeted structural test in the portfolio. It now proves the claim over everything a user installs: the package, both composition roots and the whole setup program. Its own scope is asserted alongside it, so narrowing it back to the package fails the suite rather than passing quietly.
- **The delivery scripts being exempt from the no-network scan.** They build what ships rather than shipping, so they legitimately reach the network: the Flatpak build downloads its wheels and the macOS build talks to Apple to notarise. Holding them to the application's invariant would be a claim about the wrong thing. The exemption is named in `scan.py` and asserted, so it cannot quietly grow.
- **`python-chess` behind a port rather than used directly.** It looks like an unnecessary indirection over a mature library. It is what keeps the domain pure and what would let the engine be replaced without touching the rules layer; it is why the application layer holds a 100% gate.
- **Wire format v1 being versioned at all**, for a two-player game played by email. Two installations will be on different versions eventually; a format with no version is a format that cannot ever change.
- **A pre-1.0 `VERSION` on a shipped, installable product.** That is an accurate statement about the wire format's stability, not an oversight.
- **The five separate structural suites** rather than one file of assertions. Each fails with a message about one invariant, which is what makes a red suite diagnostic rather than merely red.
- **The three independent delivery paths** (Windows installer, Linux Flatpak, macOS DMG) with `clean_flatpak.sh` scoped only to Flatpak artefacts. The scoping is deliberate so one clean cannot destroy another platform's build.
- **`installer_main.py` at the repository root**, a four-line file that looks redundant beside `installer/app.py`. It is load-bearing: a script is compiled with its own directory on the module search path, so compiling `installer/app.py` directly would leave every `installer.*` import unresolvable. Deleting it breaks the installer build.
- **The `# pragma: no branch` on the move-line branch in `export_service._narrative`.** Only a `MOVE` reaches that code; a move with nothing to report has already raised in `_subject`, so the false side cannot be reached through the public API. The pragma states that rather than a test contorting itself to fake it.
