# <img width="64" height="64" alt="postal-gambit" src="https://github.com/user-attachments/assets/fe4f922c-2ce0-445a-80d7-ab78516c1523" /> Postal Gambit

Correspondence chess over your own email. Postal Gambit is a local-first
desktop app that keeps your games, enforces the rules and turns each move
into a ready-to-send email in whatever mail client you already use. It
never touches the network itself.

Status: implemented and gated (195 tests, 100% coverage outside the UI
layer). Version 0.2.0.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): layers, invariants, execution flows
  and the design-decision record.
- [WIRE_FORMAT.md](WIRE_FORMAT.md): the versioned email wire format that
  carries moves, invitations, draw offers and resignations.
- [TESTING.md](TESTING.md): the coverage gate, the no-mocks policy and the
  structural test suite.
- [DEVELOPMENT-README.md](DEVELOPMENT-README.md): building the installer
  and packages on Windows, Linux and macOS.

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
- Import the opponent's reply by pasting the email text, or a `.pgn` file.
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
  Space both activate, and a disabled control wears a red ring instead
  of vanishing.
- Dark and light themes (View menu), persisted between runs.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.13 |
| UI | PySide6 (widgets) |
| Chess rules | python-chess, quarantined behind a port |
| Storage | One JSON file per game, local, atomic writes |
| Transport | Your mail client (`mailto:` or clipboard); no network code |
| Tests | pytest via `pytest -v --cov`, 100% gate outside the UI layer |
| Packaging | Nuitka plus bespoke installer (Windows), Flatpak, DMG |

## Install and run

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
python buildexe.py
python buildinstaller.py
```

Windows, Linux and macOS packaging are documented in
[DEVELOPMENT-README.md](DEVELOPMENT-README.md).

## Licence

GPL-3.0. See [LICENSE](LICENSE). The bundled installer carries its own
as-is notice in [INSTALLER_LICENSE](INSTALLER_LICENSE).
