# <img width="64" height="64" alt="postal-gambit" src="https://github.com/user-attachments/assets/fe4f922c-2ce0-445a-80d7-ab78516c1523" /> Postal Gambit

Correspondence chess over your own email. Postal Gambit is a local-first
desktop app that keeps your games, enforces the rules and turns each move
into a ready-to-send email in whatever mail client you already use.

**Your games never touch the network.** Your own mail client is the
transport: no server, no account, no telemetry and nothing to sign in
to. The app itself makes exactly one outbound call, disclosed here in
full: shortly after launch and once a day while running, it asks GitHub
anonymously whether a newer published release exists (Help > Check for
updates does the same on demand). If one is found you choose Download,
Skip this version or Later; a failed check stays silent and nothing is
ever downloaded or run without you choosing it. The claim is
mechanically enforced rather than merely stated:
`tests/structural/test_no_network.py` fails the suite the moment a
network import appears anywhere except the one named update-check
module, whose exemption is itself asserted so it can neither widen nor
outlive its purpose. The scan covers everything you install (the
package, both composition roots and the whole setup program) and asserts
its own reach, so narrowing it back fails the suite rather than passing
quietly.

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
- Take a move back while it is still local. A move you have played but
  not yet handed to your mail client or clipboard can be undone; once the
  email has left the application it is final, since your opponent may
  already be replying to it.
- Bulk actions across a multi-selection of games: resign, accept draws,
  delete, take back and re-send, each with eligibility filtering and
  confirmation.
- File letters and rank numbers around all four edges of the board,
  turning with it when you play Black.
- Move history panel; game names carry the same short id as the email
  subject, so a list row and its thread correlate at a glance.
- A full keyboard focus ring everywhere including dialogs: Enter and
  Space both activate; a disabled control wears a red ring instead
  of vanishing. Where focus is shows on the thing you can act on: a
  control rings, while a list marks the row you are on rather than
  outlining the whole box.
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
  you and shows the phase it is in while it works. If you asked it to
  start Postal Gambit when finished and that start does not happen, it
  says so and stays open rather than closing on a launch that never
  occurred. It keeps whatever "start Postal Gambit when I sign in"
  setting you already had. It registers the `postalgambit:` links that
  make one-click import work.
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

## Supporting the project

A donate button sits at the foot of the window, on a strip of its own below
the columns. Postal Gambit is free and stays free: there is no paid tier, no
licence key and no feature held back behind a donation.

The button does not breach the no-network invariant. It hands the address to
whatever your desktop opens links with and your browser does the asking, so
the application still opens no connection of its own. The address has one
home in the source and a structural test pins it.

## Licence

GPL-3.0. See [LICENSE](LICENSE). The bundled installer carries its own
as-is notice in [INSTALLER_LICENSE](INSTALLER_LICENSE).
