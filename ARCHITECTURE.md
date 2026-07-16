# Postal Gambit Architecture

Correspondence chess over the user's own email client. The application is a
local-first PySide6 desktop app that manages games, enforces the rules of
chess, renders outbound moves as ready-to-send emails and imports inbound
moves from pasted text. It contains no networking of any kind.

Status: implemented. Each invariant below names the structural test that
enforces it; the whole suite (unit, integration, wire-format conformance
and structural) gates at 100% coverage outside the UI layer.

## Invariants

1. **Layering**: `ui → application → domain ← infrastructure`. Domain
   imports nothing but the standard library. Application imports domain and
   stdlib only. Infrastructure implements application ports and is never
   imported by domain or application. UI is a client of application only.
   Enforced by `tests/structural/test_layer_boundaries.py`.
2. **Domain purity**: no I/O, no wall-clock reads, no randomness, no
   logging, no threading in `postalgambit/domain`. Time enters as values;
   UUIDs enter through an injected generator. Enforced by
   `tests/structural/test_domain_purity.py`.
3. **python-chess is quarantined in infrastructure** behind the
   `RulesEngine` port. No other layer imports it. If the library ever had
   to be replaced, one adapter changes. Enforced by
   `tests/structural/test_layer_boundaries.py`.
4. **No network code anywhere.** The transport is the user's mail client.
   Imports of `socket`, `http`, `urllib.request`, `smtplib`, `imaplib`,
   `poplib` and any third-party HTTP client are forbidden across the whole
   package. Enforced by `tests/structural/test_no_network.py`.
5. **PGN is the canonical game state.** Whose turn it is, game status and
   outcome are always derived from the PGN by replay, never stored beside
   it. `GameRecord` has no turn or status field by construction. Enforced
   by domain unit tests plus review.
6. **Wire format v1 is frozen** once released. Changes bump the version
   token and get a parser branch. Governance rule, documented in
   `WIRE_FORMAT.md`.
7. **One composition root** at `main.py`; constructor injection everywhere;
   no module-level singletons, no service locators. Enforced by
   `tests/structural/test_layer_boundaries.py`
   (`test_main_is_the_only_composition_root`).
8. **Modules stay at or below 400 lines.** Enforced by
   `tests/structural/test_module_size.py`.
9. **The version lives in `VERSION` only.** Runtime reads it through
   `postalgambit/version.py`; build scripts read it through a shared
   helper; nothing else hardcodes a version.
10. **Formatting is part of the suite**: black (88) and flake8 run as
    assertions in `tests/structural/test_style.py`.

## Components

```
postal-gambit/
  main.py                     composition root
  postalgambit/
    version.py                reads VERSION, 0.0.0-dev fallback
    domain/
      game.py                 GameId, Player, GameMeta, GameRecord
      identity.py             Identity: the user's own name and email
      wire.py                 WireMessage, WireAction, render/parse codec
      applink.py              postalgambit: link codec (zlib, base64url)
      subject.py              subject-line builder
      pgn_tags.py             PGN tag roster helpers
      errors.py               typed exception hierarchy
    application/
      ports.py                RulesEngine, GameStore, SettingsStore, Clock,
                              IdGenerator (Protocols)
      dto.py                  GameStatus, BoardView, MoveApplied,
                              ImportOutcome, EmailDraft
      game_service.py         create, list, resign, offer/accept draw
      move_service.py         apply my move via RulesEngine
      export_service.py       WireMessage -> email body, subject, mailto URI
      import_service.py       pasted text / .pgn file -> validated game update
    infrastructure/
      rules_pychess.py        RulesEngine adapter over python-chess
      store_json.py           one JSON file per game under the data dir
      settings_json.py        identity plus preferences (persisted theme)
      clock.py, ids.py        SystemClock, Uuid4Generator
    ui/
      main_window.py          menu bar, game list, board, status, theme apply
      menus.py                File, Game, View (theme toggle) and Help menus
      actions.py              selection-aware bulk flows (resign, draw,
                              delete, re-send) with per-game export dialogs
      board_widget.py         QGraphicsView board, click-click moves, rounded
                              corners, theme tokens injected at runtime
      side_panel.py           app badge above the numbered move history
      labels.py               humanised game names (date, time, short id)
      launch.py               single-instance server plus app-link forwarding
      keyboard_nav.py         explicit focus ring (the Fulcrum model)
      icons.py                bundled asset resolution across dev and builds
      dialogs/                new game, import, export preview, about, licence
      theme.py                semantic dark/light token dicts and stylesheet
  tests/                      mirrors the package, plus tests/structural/
  assets/                     generated icon set (generate_icons.py)
```

### Domain

Frozen dataclasses (`frozen=True, slots=True`, tuples for collections).
`GameRecord` holds `GameMeta` plus the PGN text. One piece of protocol
state lives beside the PGN rather than in it: `draw_offer_open` on
`GameMeta`, because a draw offer is wire-protocol state that PGN cannot
carry; everything chess-derivable stays derived. The wire codec is pure
string work (render a `WireMessage` to a block, parse text back to one) so
it lives in the domain: it is the protocol contract and must be testable
with zero machinery. The codec parses structure only; chess legality is not
its job.

### Application

Ports are Protocols. `RulesEngine` is the single seam through which chess
knowledge flows: replay PGN, validate and apply a SAN move, list legal
target squares, report outcome and produce a `BoardView` DTO (an 8x8 map of
piece codes) for the UI. Services orchestrate: a move flows in from the UI
as source and target squares, comes back as SAN from the rules engine, is
appended to the PGN, persisted and handed to the export service.

### Infrastructure

- `rules_pychess.py`: the only file that imports python-chess (GPL-3.0,
  matching the project licence). Covers legality, SAN, FEN, PGN round-trip
  and all draw and mate outcomes.
- `store_json.py`: one versioned JSON document per game
  (`{"version": 1, "meta": {...}, "pgn": "..."}`) in
  `~/.postal-gambit/games/<game-id>.json`. Atomic writes via temp file and
  `os.replace()`. Single writer, the app itself.
- `settings_json.py`: `~/.postal-gambit/settings.json` for the user's own
  name and email (stamped into PGN tags) and UI preferences.

### UI

PySide6 widgets. The board is a `QGraphicsView` canvas stop inside the
standard explicit focus ring: Tab/Right and Shift+Tab/Left step the ring,
Up/Down move the square cursor inside the board, Enter selects and drops,
Escape cancels a pending selection. Board orientation puts the user's
colour at the bottom. Every destructive action (delete game, overwrite on
divergent import) gets a modal confirmation naming the target.

Two themes (dark and light) share one semantic token set in `theme.py`.
The View menu toggles them; the choice persists through the settings
store; `main_window._apply_theme` restyles the application and hands the
token dict to the board, which repaints from injected tokens rather than
reading module state. The board's outer corners are rounded by a clip item
in the scene, so the squares stay square inside a rounded silhouette.

`launch.py` gives the app single-instance behaviour over a `QLocalServer`
(newline-framed, server-close acknowledged): a second launch forwards its
command line to the running window and exits. The same channel carries
clicked `postalgambit:` links.

## Execution flows

**New game**: wizard collects opponent name, email and my colour. The
service mints a GameID, builds the PGN tag roster from settings identity,
persists, then offers an invitation export (Action `invite`) when the
opponent moves first; otherwise it goes straight to the board.

**My move**: board interaction produces source and target squares. The
rules engine validates and returns SAN plus the updated PGN. The record is
persisted, then the export dialog shows the exact email (subject and body,
preamble, block, footer) with two buttons: "Open in mail client" (a
`mailto:` URI launched through `QDesktopServices.openUrl`) and "Copy email
to clipboard". On Windows the mailto URI is launched with `os.startfile`
(the ShellExecute path, which honours the per-user MAILTO default) rather
than Qt's openUrl, whose Windows mail branch consults the legacy
`Software\Clients\Mail` registry and can resurrect a stale Outlook entry;
other platforms use `QDesktopServices.openUrl`. The mailto body is
percent-encoded UTF-8 with CRLF line breaks; if the encoded URI exceeds `MAILTO_URI_MAX` (a named constant,
around 6000 characters) the dialog steers to the clipboard path, since some
client and shell combinations truncate long URIs.

**Inbound move**: the user pastes email text into the import dialog (or
opens a `.pgn` file). The codec finds and parses the block per
`WIRE_FORMAT.md`; the import service routes by GameID, replays the PGN,
verifies the strict-prefix rule and turn consistency, persists and updates
the board. Unknown GameID offers game creation (that is the invite path):
the opponent's address comes from the block's optional `From` header,
shown in the confirmation before the game is created, and the app asks
for it only when the header is absent (an older sender or hand-typed
text). The header is a convenience default, never an authenticated
identity. No block found falls back to bare-SAN parsing against a
user-chosen game. Divergence is reported and never auto-resolved.

**Import link**: every outbound email also carries an https link (the
block compressed with zlib and encoded base64url in the URL fragment,
codec in `domain/applink.py`), because mail clients auto-link https where
they leave a custom scheme inert. The link opens a static page
(`docs/open/`, served by GitHub Pages) that rebuilds the
`postalgambit:` URI locally, auto-attempts the launch and shows a
high-contrast Open button; a fragment is never sent to any server. The
launcher forwards the URI to a running instance when there is one; the
window decodes it and opens the import dialog prefilled with the block,
so exactly the same validation and the same explicit Import click apply
as for a paste. Either link form pastes into the import dialog too. The
URI scheme is registered per user by the Windows installer, the Flatpak
manifest and the macOS bundle.

## Design decisions

| Decision | Choice | Rationale | Rejected |
|---|---|---|---|
| Transport | User's own mail client via `mailto:` and clipboard | Removes the entire mail-infrastructure class (IMAP, SMTP, OAuth, credentials, polling); the mail client is the compatibility interface | Built-in IMAP/SMTP client; a central server |
| UI stack | PySide6 widgets | Established delivery lineage (Nuitka, installer, Flatpak, DMG, keyboard nav); no mail plumbing left to favour Go | Go + Wails (its advantage died with the transport decision); web app |
| Rules | python-chess behind a port | Best rules library in any language; full draw rules, SAN, PGN; quarantined so the domain stays stdlib-pure | Reusing console-chess C++ (Win32-locked, I/O-coupled, incomplete rules); hand-rolling rules |
| Canonical state | PGN text, everything else derived | One source of truth, no drift; every email carries full state so lost mail never corrupts | Storing turn/status fields; move-list-plus-position storage |
| Storage | One JSON file per game | Document-shaped, low volume, trivially portable and inspectable; atomic replace writes | SQLite (relational shape not needed); one big JSON file (write amplification, single hot file) |
| Wire framing | PEM-style BEGIN/END block | Instantly recognisable, robust to paste, quote-stripping is easy, versioned in the delimiter | Attachments (mailto cannot attach); JSON payload (hostile to app-less opponents); bare PGN (no action semantics) |
| Board diagram in email | ASCII letters, informational only | Survives proportional fonts and every client; Unicode chess glyphs render unevenly | Unicode glyph diagram; HTML mail |
| Import posture | Liberal accept: any legal strict extension | Postel's law; recovers cleanly from a missed email | Exactly-one-ply rule (brittle) |
| Draw and resign | Wire `Action` header plus PGN `Result`/`Termination` | Correspondence play genuinely needs both; maps cleanly onto standard PGN | Deferring them (would force out-of-band agreement) |
| Game identity | uuid4 in a `GameID` PGN tag | The `.pgn` file alone stays a complete routable record; short form for humans | ID in block header only; deriving identity from players plus date |
| Engine assistance | None, ever | The product is human correspondence chess; "no machines" is scope, not just a default | Optional analysis mode |
| i18n | Deferred; strings centralised from day one | Not core to v1; centralising early keeps the JSON-locale pattern cheap to adopt later | Qt Linguist |
| Theming | Semantic colour tokens, dark and light dicts, runtime toggle persisted in settings | Widget code never names a colour, so a theme is one dict; the board takes tokens by injection | Qt palettes; per-widget styling |

## Quality enforcement

- pytest with `--cov-fail-under=100` over the `postalgambit` package with
  `ui/` and `version.py` omitted (coverage source and omit list live in
  `pyproject.toml`, so `pytest -v --cov` and plain `pytest` measure the
  same thing). No mock libraries: hand-written fakes implement the ports
  (an in-memory `GameStore`, a scripted `Clock`, a fixed `IdGenerator`).
  The python-chess adapter is tested against the real library, which is
  pure computation and needs no test doubles. See `TESTING.md`.
- Structural tests as listed under Invariants: layering by AST scan, domain
  purity, no-network, module size, composition-root whitelist, style.
- Wire-format conformance tests mirror `WIRE_FORMAT.md` section by section,
  including quoted-reply stripping, unknown versions, unknown actions,
  divergence and multi-move catch-up.

## Delivery

Implemented: `buildexe.py` (Nuitka, standalone, PE metadata,
`assets/postal-gambit.ico`) builds straight into the installer payload;
`buildinstaller.py` zips the payload and wraps the themed bespoke
per-user installer as `dist-installer/PostalGambitSetup.exe`;
`build_flatpak.sh` and `builddmg.py` cover Linux and macOS. App id
`uk.codecrafter.PostalGambit`. All three register the `postalgambit:` URI
scheme. The icon set is generated from the repo-root master by
`generate_icons.py`. The version lives in `VERSION` only. Build steps per
platform are in `DEVELOPMENT-README.md`.
