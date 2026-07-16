# Postal Gambit

Correspondence chess over your own email. Postal Gambit is a local-first
desktop app that keeps your games, enforces the rules and turns each move
into a ready-to-send email in whatever mail client you already use. It
never touches the network itself.

Status: design phase. The architecture and wire format are specified
(`ARCHITECTURE.md`, `WIRE_FORMAT.md`); implementation follows.

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
  clipboard flow, but there is no in-app sending and never will be.

## What it does

- Manages any number of ongoing games: whose move, full history, archive.
- Full rules enforcement including all draw rules, via python-chess.
- Export your move as a pre-filled email draft (`mailto:`) or to the
  clipboard: readable preamble, ASCII board, then a delimited PGN block
  that carries the entire game state (see `WIRE_FORMAT.md`).
- Import the opponent's reply by pasting the email text, or a `.pgn` file.
  Divergence is detected and reported, never silently resolved.
- Invitations, draw offers, draw acceptance and resignation over the same
  format.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.13 |
| UI | PySide6 (widgets) |
| Chess rules | python-chess, quarantined behind a port |
| Storage | One JSON file per game, local, atomic writes |
| Transport | Your mail client (`mailto:` or clipboard); no network code |
| Tests | pytest, 100% coverage gate outside the UI layer |
| Packaging | Nuitka plus bespoke installer (Windows), Flatpak, DMG |

## Install and run

Implementation pending. The intended developer loop:

```
pip install -r requirements.txt -r requirements-dev.txt
python main.py
```

## Test

```
pytest
```

## Build

```
python buildexe.py
python buildinstaller.py
```

## Licence

GPL-3.0. See `LICENSE`.
