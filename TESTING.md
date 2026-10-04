# Testing Postal Gambit

The whole suite runs with one command and one hard gate:

```
pytest -v --cov
```

Coverage must be 100% over the measured surface, line and branch;
anything less fails the run (`--cov-fail-under=100 --cov-branch`). The
exit code is authoritative: 0 means every test passed and the gate was
met. No test count is quoted here on purpose: it is a number that would
have to be remembered on every change and would be wrong the first time
it was not. Coverage source and omissions are
configured in `pyproject.toml`, so a bare `--cov`, the configured addopts
and plain `pytest` all measure the same thing; the repo root is on
`sys.path` via the `pythonpath` ini setting, so the `pytest` launcher and
`python -m pytest` behave identically.

Running a subset trips the gate by design; use `--no-cov` for partial
runs:

```
pytest tests/domain/test_wire.py --no-cov
```

## What is measured

100% is enforced over `postalgambit/domain`, `postalgambit/application`,
`postalgambit/infrastructure`, `installer/ops` and `installer/state`. The
setup program does the most privileged work in the product (registry
writes, the `postalgambit:` URI registration, shortcut creation, per-user
deployment, uninstall), so its two Qt-free halves are gated rather than
left unmeasured. Omitted, with rationale:

- `postalgambit/ui/*`: PySide6 widget code. UI tests over real Qt are
  brittle in headless environments and mocked Qt is forbidden, so the UI
  is verified by structural tests plus behavioural probes, not a line
  gate.
- `postalgambit/version.py`: a file read with a fallback constant.
- `main.py`: the composition root; wiring, no logic.
- `installer/ui/*`, `installer/app.py`, `installer/cli.py`,
  `installer/constants.py` and `installer/shared/*`: the setup program's Qt
  client and its wiring, omitted on the same grounds as
  `postalgambit/ui`.

## The installer suite

`tests/installer/` exercises the setup program's operations without ever
touching a real Postal Gambit installation. Three seams make that
possible; each has a fixture in `tests/installer/conftest.py`:

- **`scratch_keys`**: every HKCU location the installer writes is a field
  on an injected `RegistryKeys` value, including the `postalgambit:` URI
  scheme key. The fixture yields a unique key under
  `Software\PostalGambitInstallerTests\<uuid>` and deletes the tree
  afterwards, so a test never reads or alters the user's own
  registration.
- **`isolated_profile`**: the per-user paths come from `USERPROFILE`,
  `LOCALAPPDATA` and `APPDATA`, so the fixture redirects the profile into
  a temporary tree. The app's own `~/.postal-gambit` follows it.
- **`staged_payload`**: the payload is anchored on the installer package
  directory, so the fixture points that anchor at a temporary tree. The
  real `installer/payload/PostalGambit.zip` is the full build output and
  no test opens it; a few-byte zip stands in.

Every external command goes through the `CommandRunner` protocol, so
`tests/installer/fakes.py` carries one recording fake of it. No test ends
a real process, writes a real shortcut or spawns a real `taskkill`.

## The Qt application object

Qt permits exactly one application object per process and it cannot be
upgraded afterwards, so `tests/conftest.py` builds a `QApplication` at import
time, before any test module loads. Two suites want one and they want
different things: the setup program's worker tests need only an event loop,
while the focus-chain suite needs widgets. Whichever ran first would claim the
singleton; since `tests/installer` sorts before `tests/structural`, a bare
`QCoreApplication` won and left every widget test erroring on a missing
`setStyleSheet`.

A `QApplication` is a `QCoreApplication`, so it satisfies both. The worker
tests keep their own fixture and reuse whatever instance exists; the claim
their docstring makes, that the setup program's plumbing needs no widget, is
about the production code rather than about this process. The offscreen
platform is selected first, so nothing here wants a display.

## Policy: no mocks

No mock libraries anywhere. Test doubles are hand-written fakes
implementing the application ports: an in-memory `GameStore`, a scripted
`Clock`, a fixed `IdGenerator` (see `tests/fakes.py`). The python-chess
adapter is tested against the real library, which is pure computation and
needs no double. Storage tests use real files in pytest tmp directories.

## Layers

| Layer | Test type | I/O |
|---|---|---|
| domain | pure unit | none |
| application | unit, hand-written fakes for ports, real python-chess | none |
| infrastructure | integration, real files in tmp dirs | tmp only |
| installer ops and state | integration, redirected profile, scratch registry keys, fake command runner | tmp and scratch HKCU |
| ui | behaviour over a real QApplication, offscreen, stand-in ports | none |
| structural | AST and source scans over what ships, plus the test tree for size; the focus-chain suite also builds real widgets offscreen | file reads |

## Structural suite

`tests/structural/` enforces the architecture invariants named in
[ARCHITECTURE.md](ARCHITECTURE.md):

- `test_layer_boundaries.py`: layering direction, third-party quarantine
  (python-chess in one adapter, PySide6 in `ui/` only), `main.py` as the
  only composition root.
- `test_domain_purity.py`: no I/O, wall-clock reads, randomness, logging
  or threading in the domain.
- `test_no_network.py`: no network imports anywhere in what ships, with
  the update check's GitHub adapter as the single named exemption. The
  scan covers the package, `main.py`, `installer_main.py` and the whole
  `installer/` tree. It asserts its own reach too, so narrowing it back
  to the package fails rather than passing quietly. It also asserts the
  exemption whole: the exempt module must ship, must import
  `urllib.request` and may import nothing forbidden beyond it. Beyond the
  network modules it flags the indirect routes (Qt networking other than
  the two local-socket classes, `asyncio`, `importlib`, `__import__`,
  `webbrowser`, `multiprocessing`, `subprocess` outside its two named
  holders); each route is planted in a scratch module as a positive
  control and must be flagged.
- `test_plain_text.py`: no `QLabel(...)` or `QMessageBox` box is built
  anywhere in `ui/` except `ui/plain_text.py`, which fixes the format to
  plain text, so a correspondent's words are never rendered as markup that
  loads what it names. A planted label is a positive control.
- `test_module_size.py`: every module at or below 400 lines, plus the 5%
  danger band as a second assertion so a file at 399 is caught before the
  next edit breaks the cap for an unrelated reason. The band is derived
  from the cap rather than written as a second literal. Scope is what
  ships plus the test tree, which grows the same way source does. The
  staged payload is build output and the delivery scripts are linear
  recipes, so both are out of scope; the exemption is named in
  `tests/structural/scan.py` and asserted.
- `test_style.py`: black (88) and flake8 run as in-suite assertions over
  the package, the tests, the setup program and every build script.
- `test_focus_rings.py`: no stylesheet rule paints a ring on a pane. A Qt
  class selector matches every subclass, so a ring named against a
  container would reach every scroll area, list and label in the app; an
  item view gets no ring in any state, its current row being the
  indicator; no region rings on hover; no text view ties a border to any
  state (focus, hover, disabled), the editable paste box being the one
  exemption, named by object name and proved editable at runtime. It reads
  the sheet `build_qss` actually returns rather than its source, plus the
  setup program's sheet. It carries positive controls asserting the scanner
  can see a ring at all and names each planted text-view ring, because the
  other checks pass trivially if it cannot.
- `test_focus_chain.py`: no pane is reachable by Tab. It walks the
  toolkit's own focus chain for the main window and every dialog, which
  is what makes the answer equal to what a real Tab press reaches, then
  asserts every stop is something the user can act on. A read-only
  scrolling region is checked both ways: a stop while it overflows, off
  the ring when it fits.
- `test_donate.py`: the donation address is the one generated for this
  application, is reached over https and has exactly one home in the
  source; the button leaves through the `ui/links.py` seam, which may
  import nothing beyond Qt. The two call sites that predate that seam are
  named, so a new direct caller of the desktop opener fails rather than
  slipping in. It also pins the wiring the UI gate cannot see: the button
  is connected, it is in the focus ring, the tray is not itself a stop, the
  tooltip says a browser opens and a desktop that declines is reported.

## UI behaviour

`tests/ui/` holds behaviour the structural scans cannot see, over a real
`QApplication` on the offscreen platform with nothing in Qt mocked. These
tests sit outside the line gate with the rest of `postalgambit/ui`.

- `test_update_check_after_close.py`: hardening for an update check whose
  controller is deleted while it is out. The release source is held open
  on an event, the window is deleted (taking the controller with it), the
  answer is released and the worker joined; nothing may reach
  `threading.excepthook`. Closing or quitting the app was measured not to
  delete the controller, so the test forces the deletion directly.
- `test_plain_text_widgets.py`: an `<img>` naming a real picture is put in
  the status headline and the export "To:" line; every label must be plain
  text and the headline's size hint must not grow to hold the picture.
- `test_damaged_store.py`: the real window is built (never shown, no update
  check wired) over a games folder holding one damaged file beside a good
  game; it must build, list the good game and leave the damaged file
  byte-identical.
- `test_panes_are_not_stops.py`: every app dialog and every setup-program
  surface (window, both licences, a short notice, close-app, uninstall) is
  shown offscreen; a reading pane (a scroll area that is read, not an item
  view and not editable text) fails in three cases: a click could focus it;
  it is a Tab stop while it fits; its dialog opens on it. The chain is walked
  from the window, never from `focusWidget()`; offscreen never activates a
  window, so a dialog with no focus of its own is taken to open on its first
  stop, as measured on Windows. A planted dialog shows each failure named.
- `test_auto_scroller.py`: the reading cycle over BOTH copies of the
  scroller (application and setup program), so they cannot drift. Each
  scroller's timer is asserted running and then stopped; the tick is called
  by hand, never waited on. Covers the canon constants, the start hold
  (surviving the dialog's own opening focus), the half-pace descent, the
  holds and the fast rewind at both ends, suspension by wheel, click, key,
  scrollbar and focus with resumption in place, the rewind after a pause at
  the bottom, a surface that fits costing nothing, a modal above freezing
  time and input alike, a modal's own surface still reading, no focus policy
  changed and the refusal of a `QPlainTextEdit`.
- `test_reading_surfaces_scroll.py`: About and the licence carry a scroller,
  as do both setup-program licences; the Export body and the Import paste
  box do not; and a source scan proves only those two dialog modules attach
  one, so no item view or working text gains it unnoticed.

## The Nuitka gate

`tests/delivery/test_build_utils.py` covers the check the build scripts run
before compiling; it sits outside the line gate with the rest of the delivery
scripts. It builds a scratch venv without pip (an interpreter with no
Nuitka) and asserts the check reads that interpreter rather than the one
running the test, then refuses with the install command for it. It asserts the
two Windows scripts pass the interpreter they compile with, that the floor is
the `nuitka>=` line of `requirements-dev.txt` and that a requirements file
without that line stops the build with a reason. No test runs a build.

## Wire-format conformance

`tests/domain/test_wire.py` mirrors [WIRE_FORMAT.md](WIRE_FORMAT.md)
section by section: framing, quoted-reply stripping, unknown versions,
unknown actions and divergence detection. What a receiver refuses is
covered against the real rules engine in
`tests/application/test_import_hostile.py` (a claimed ending on a move, an
unoffered draw accept, a null move, a set-up position, a new or altered
move for the receiver's side, a bare PGN, an app-less reply above a quoted
email; a multi-move catch-up replaying the receiver's stored moves is
accepted) and
against real files in `tests/infrastructure/test_store_hostile.py` (a
traversing or case-variant GameID, a damaged file beside good ones). The
`postalgambit:` link codec is covered the same way in
`tests/domain/test_applink.py`.

## Reading the output

Coverage-gated pytest prints the coverage table last and no "N passed"
summary above it in some configurations, so do not grep for text: read
the exit code. A quick count without coverage: `pytest --no-cov -q`.
