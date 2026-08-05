# Postal Gambit: Technical Debt

A standing reference to the project's outstanding technical debt. It records what is still open, weighs whether each item is worth doing and gives the rationale. Every item is a behaviour-preserving internal concern: nothing here proposes reverting a feature or changing any UI or UX behaviour. Scope is the whole repository (the `postalgambit` package, the composition root, the bespoke installer, the delivery scripts for Windows, Linux and macOS, and the GitHub Pages site) read against `ARCHITECTURE.md`, `WIRE_FORMAT.md`, `TESTING.md` and the tests under `tests/structural/`.

This project is in strong shape. Five structural suites (domain purity, layer boundaries, module size, style and a no-network invariant) share one AST scanner, the package and the setup program's Qt-free halves are gated at 100% line and branch coverage, `VERSION` is the single source of truth, and there is not a single em dash or hardcoded version string in the tree. The list below is short, and item 1 is the only one that touches the product's central promise.

---

## 1. The no-network invariant is enforced over the package, not over what ships

`tests/structural/test_no_network.py` is the best test in this repository. It forbids any import of `socket`, `requests`, `urllib3`, `urllib.request` or `urllib.error`, which makes the project's defining claim mechanically checkable: Postal Gambit exchanges moves as email messages that the *user* sends, and the application itself never opens a connection.

`tests/structural/scan.py` sets `PACKAGE_ROOT = REPO_ROOT / "postalgambit"` and every structural suite iterates from there. So the invariant is proven for the package and is unproven for:

- `main.py`, the composition root
- `installer/` and `installer_main.py`, the setup program
- the delivery scripts

None of those is likely to open a socket today, and the setup program extracts a bundled payload rather than downloading one. That is not the point. The claim on the site and in the README is about the product a user installs, and the test that backs it stops at the package boundary. A future "check for updates" button in the installer, or an analytics call added to `main.py`, would pass the suite untouched.

Widen the scan to the repository's shipped Python (package, `main.py`, `installer/`) for this one test, with the delivery scripts explicitly exempted and the exemption written down. `test_module_size.py` now shows the shape to copy: it scans the package plus a named list of extra trees. That converts the strongest guarantee in the project from true-of-most-of-it into true-of-all-of-it, and it is perhaps twenty lines of work.

## 2. Three modules sit at the edge of the cap

- `postalgambit/ui/main_window.py` at 357
- `tests/application/test_import_service.py` at 358
- `builddmg.py` at 367 (a delivery script, exempt by design)

The first two are comfortably under 400 and clear of the 381 to 399 danger band, so nothing needs doing today. They are noted because `test_module_size.py` enforces the cap and nothing warns before it: adding a second assertion at 380 would give a signal one edit earlier, which is when it is cheap to act on.

## 3. The UI layers are omitted from the gate in full

`[tool.coverage.run]` measures `postalgambit`, `installer.ops` and `installer.state`, with `postalgambit/ui/*` and `version.py` omitted; `installer/ui`, `installer/app.py`, `installer/cli.py` and `installer/shared` are simply outside the source list. The version module is a file read and the UI omissions are the standard portfolio position, correct for painting and layout.

It is recorded so the omission is never read as "the UI has no logic". `main_window.py` at 357 lines is the largest module in the package, and a correspondence-chess client's window carries real decisions: which moves are legal to offer, when a game is awaiting the opponent, what happens on an out-of-order message. `postalgambit/application` is where those belong, and the port-behind-`python-chess` design means most of it can move there.

This is continuous work rather than a task with an end state.

---

## Looks like debt, not worth touching

- `builddmg.py` at 367 lines and the other delivery scripts. Linear recipes, exempt from the cap by design.
- `INSTALLER_LICENSE` beside `LICENSE`. The installer wrapper carries an as-is notice distinct from the application licence. Deliberate and load-bearing.
- The fourteen tracked PNGs plus the `.ico` and `.icns`. Emitted by `generate_icons.py` from a single master and consumed by named packaging paths on three platforms.
- `WIRE_FORMAT.md` as a separate document from `ARCHITECTURE.md`. The wire format is a compatibility contract between two installations that may be on different versions; it deserves its own file and its own version discipline.
- `tests/structural/scan.py` being a helper module inside the test tree rather than a package. One scanner shared by five suites is exactly right.

## Not debt (do not "fix" these)

These look like candidates but are correct as they stand; changing them would regress or add cost for nothing.

- **`test_no_network.py` itself.** It is the mechanism that makes "the app never touches the network" a fact rather than a marketing line, and it is the single best-targeted structural test in the portfolio. Item 1 widens its scope; nothing here weakens it.
- **`python-chess` behind a port rather than used directly.** It looks like an unnecessary indirection over a mature library. It is what keeps the domain pure and what would let the engine be replaced without touching the rules layer, and it is why the application layer holds a 100% gate.
- **Wire format v1 being versioned at all**, for a two-player game played by email. Two installations will be on different versions eventually; a format with no version is a format that cannot ever change.
- **`VERSION` at `0.2.0` on a shipped, installable product.** Pre-1.0 is an accurate statement about the wire format's stability, not an oversight.
- **The five separate structural suites** rather than one file of assertions. Each fails with a message about one invariant, which is what makes a red suite diagnostic rather than merely red.
- **The three independent delivery paths** (Windows installer, Linux Flatpak, macOS DMG) with `clean_flatpak.sh` scoped only to Flatpak artefacts. The scoping is deliberate so one clean cannot destroy another platform's build.
- **`installer_main.py` at the repository root**, a four-line file that looks redundant beside `installer/app.py`. It is load-bearing: a script is compiled with its own directory on the module search path, so compiling `installer/app.py` directly would leave every `installer.*` import unresolvable. Deleting it breaks the installer build.
- **The `# pragma: no branch` on the move-line branch in `export_service._narrative`.** Only a `MOVE` reaches that code, and a move with nothing to report has already raised in `_subject`, so the false side cannot be reached through the public API. The pragma states that rather than a test contorting itself to fake it.
