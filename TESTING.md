# Testing Postal Gambit

The whole suite runs with one command and one hard gate:

```
pytest -v --cov
```

325 tests. Coverage must be 100% over the measured surface, line and
branch, or the run fails (`--cov-fail-under=100 --cov-branch`). The exit
code is authoritative: 0 means
every test passed and the gate was met. Coverage source and omissions are
configured in `pyproject.toml`, so a bare `--cov`, the configured addopts
and plain `pytest` all measure the same thing, and the repo root is on
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
possible, and each has a fixture in `tests/installer/conftest.py`:

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
  real `installer/payload/PostalGambit.zip` is about 35 MB, and no test
  opens it; a few-byte zip stands in.

Every external command goes through the `CommandRunner` protocol, so
`tests/installer/fakes.py` carries one recording fake of it. No test ends
a real process, writes a real shortcut or spawns a real `taskkill`.

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
| structural | AST and source scans over the package | file reads |

## Structural suite

`tests/structural/` enforces the architecture invariants named in
[ARCHITECTURE.md](ARCHITECTURE.md):

- `test_layer_boundaries.py`: layering direction, third-party quarantine
  (python-chess in one adapter, PySide6 in `ui/` only), `main.py` as the
  only composition root.
- `test_domain_purity.py`: no I/O, wall-clock reads, randomness, logging
  or threading in the domain.
- `test_no_network.py`: no network imports anywhere in the package.
- `test_module_size.py`: every module at or below 400 lines, across the
  package and `installer/` alike. The staged payload is build output and
  the delivery scripts are linear recipes, so both are out of scope.
- `test_style.py`: black (88) and flake8 run as in-suite assertions over
  the package, the tests, the setup program and every build script.

## Wire-format conformance

`tests/domain/test_wire.py` mirrors [WIRE_FORMAT.md](WIRE_FORMAT.md)
section by section: framing, quoted-reply stripping, unknown versions,
unknown actions, divergence detection and multi-move catch-up. The
`postalgambit:` link codec is covered the same way in
`tests/domain/test_applink.py`.

## Reading the output

Coverage-gated pytest prints the coverage table last and no "N passed"
summary above it in some configurations, so do not grep for text: read
the exit code. A quick count without coverage: `pytest --no-cov -q`.
