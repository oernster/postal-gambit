# <img width="64" height="64" alt="postal-gambit" src="https://github.com/user-attachments/assets/fe4f922c-2ce0-445a-80d7-ab78516c1523" /> Postal Gambit

Correspondence chess over your own email. Postal Gambit is a local-first
desktop app that keeps your games, enforces the rules and turns each move
into a ready-to-send email in whatever mail client you already use.

**It never touches the network itself.** There is no networking code in
the application at all: no server, no account, no telemetry and nothing
to sign in to. Your own mail client is the transport; the claim is
mechanically enforced rather than merely stated, because
`tests/structural/test_no_network.py` fails the suite the moment any
network import appears. The scan covers everything you install (the
package, both composition roots and the whole setup program). It asserts
its own reach too, so narrowing it back fails the suite rather than
passing quietly.

Status: implemented and gated at 100% line and branch coverage over the
package and over the setup program's Qt-free halves.

Website: https://ernster.dev/postal-gambit/

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): layers, invariants, execution flows
  and the design-decision record.
- [WIRE_FORMAT.md](WIRE_FORMAT.md): the versioned email wire format that
  carries moves, invitations, draw offers and resignations.
- [TESTING.md](TESTING.md): the coverage gate, the no-mocks policy and the
  structural test suite.
- [DEVELOPMENT-README.md](DEVELOPMENT-README.md): building the installer
  and packages on Windows, Linux and macOS.
- [TECH_DEBT.md](TECH_DEBT.md): what is still open, what is deliberately left
  and what only looks like debt.

## Who it is for

- People who want slow, thoughtful chess with a friend by email, the way
  postal chess used to work.
- Players whose opponent may not even have the app: moves arrive as
  readable text and a plain-text reply like `Nf6` imports fine.

## Who it is not for

- Real-time or online chess. Use Lichess.
- Anyone wanting engine analysis. Postal Gambit ships none, deliberately;
  "no machines" is the point.
- Webmail-only users without any mail client are still fine via the
  clipboard flow; there is no in-app sending and never will be.

## What it does

- Manages any number of ongoing games: whose move, full history, archive.
- Full rules enforcement including all draw rules, via python-chess.
- Export your move as a pre-filled email draft (`mailto:`) or to the
  clipboard: readable preamble, ASCII board, then a delimited PGN block
  that carries the entire game state (see
  [WIRE_FORMAT.md](WIRE_FORMAT.md)).
- Import the opponent's reply by pasting the email text or a `.pgn` file.
  Divergence is detected and reported, never silently resolved.
- One-click import: every outbound email carries an https link that works
  in any mail client; a static page bounces it to the installed app with
  the move prefilled, routed to the running instance when there is one.
- Invitations, draw offers, draw acceptance and resignation over the same
  format. A game arriving as an invitation or first move is created with
  the opponent's reply address taken from the message itself, so nothing
  needs typing.
- Bulk actions across a multi-selection of games: resign, accept draws,
  delete and re-send, each with eligibility filtering and confirmation.
- Move history panel; game names carry the same short id as the email
  subject, so a list row and its thread correlate at a glance.
- A full keyboard focus ring everywhere including dialogs: Enter and
  Space both activate; a disabled control wears a red ring instead
  of vanishing.
- Dark and light themes (View menu), persisted between runs.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.11 or newer (`pyproject.toml` is the authority; development runs on 3.13) |
| UI | PySide6 (widgets) |
| Chess rules | python-chess, quarantined behind a port |
| Storage | One JSON file per game, local, atomic writes |
| Transport | Your mail client (`mailto:` or clipboard); no network code |
| Tests | pytest via `pytest -v --cov`; 100% line and branch gate outside the Qt code |
| Packaging | Nuitka plus a bespoke per-user installer (Windows), Flatpak (Linux), DMG (macOS) |

## Install

Ready-made packages for all three platforms are on the
[releases page](https://github.com/oernster/postal-gambit/releases). The
download buttons on the website always point at the newest one.

- **Windows**: `PostalGambitSetup.exe`. A per-user setup program that
  needs no administrator rights. It offers to close a running copy for
  you and shows the phase it is in while it works. It keeps whatever
  "start Postal Gambit when I sign in" setting you already had. It
  registers the `postalgambit:` links that make one-click import work.
- **macOS**: `postal-gambit.dmg`. Open it and drag Postal Gambit into
  Applications.
- **Linux**: `postal-gambit.flatpak`. Install it with
  `flatpak install --user postal-gambit.flatpak`.

## Run from source

```
pip install -r requirements.txt -r requirements-dev.txt
python main.py
```

## Test

```
pytest -v --cov
```

See [TESTING.md](TESTING.md) for the gate, the layout and the policy.

## Build

```
python buildexe.py         # Windows: the standalone app, straight into the payload
python buildinstaller.py   # Windows: the setup program around that payload
./build_flatpak.sh         # Linux
python builddmg.py         # macOS
```

Each platform's prerequisites and the release checklist are in
[DEVELOPMENT-README.md](DEVELOPMENT-README.md).

## Licence

GPL-3.0. See [LICENSE](LICENSE). The bundled installer carries its own
as-is notice in [INSTALLER_LICENSE](INSTALLER_LICENSE).
