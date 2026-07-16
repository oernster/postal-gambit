# Postal Gambit Wire Format v1

Status: draft, frozen on first release. Any breaking change bumps the version
token in the BEGIN line; parsers reject versions they do not know.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are to be
interpreted as described in RFC 2119 and RFC 8174.

## 1. Purpose

Postal Gambit plays correspondence chess over ordinary email. The application
never sends or receives mail itself; the user's own mail client is the
transport. This document defines the only contract both sides need to agree
on: a delimited text block embedded in the email body. A recipient without
the application can read the move as plain text and reply in kind; a
recipient with the application pastes the email text and the game advances.

## 2. Message anatomy

An outbound email is composed of three parts. Only the second is normative.

1. A human-readable preamble: the move in Standard Algebraic Notation (SAN),
   whose turn it is and an ASCII board diagram. Informational only; parsers
   MUST NOT read it.
2. The Postal Gambit block, defined below.
3. A footer identifying the application. Informational only.

## 3. The block

```
-----BEGIN POSTAL GAMBIT v1-----
Action: move
Offer: draw

[Event "Postal Gambit correspondence game"]
[Site "email"]
[Date "2026.07.16"]
[Round "-"]
[White "Oliver Ernster"]
[Black "Jane Doe"]
[Result "*"]
[GameID "5f3a9c2e-8d41-4b7a-9e6f-2c1d0a8b7e55"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *
-----END POSTAL GAMBIT-----
```

Structure, in order:

- The BEGIN line, exactly `-----BEGIN POSTAL GAMBIT v1-----`.
- One or more header lines of the form `Name: value`.
- One blank line.
- A complete PGN game: the Seven Tag Roster, a `GameID` tag and the full
  movetext from move one through the sender's latest move.
- The END line, exactly `-----END POSTAL GAMBIT-----`.

The PGN is the entire game state. Every message carries the full game from
the first move, never a delta; a lost or out-of-order email therefore never
corrupts state, the latest message always suffices.

## 4. Headers

| Header | Values | Required | Meaning |
|---|---|---|---|
| `Action` | `invite`, `move`, `draw-accept`, `resign` | yes | What this message does |
| `Offer` | `draw` | no | A draw offer accompanying a move |

- `invite`: proposes a new game. The PGN movetext MAY be empty (`*` only)
  when the recipient moves first. The recipient's application offers to
  create the game locally.
- `move`: the PGN extends the previous state by the sender's move.
- `draw-accept`: accepts a standing draw offer. The PGN `Result` MUST be
  `1/2-1/2` and a `[Termination "agreed draw"]` tag SHOULD be present.
- `resign`: the PGN `Result` MUST be `1-0` or `0-1` (the winner is the
  non-sender) and a `[Termination "resignation"]` tag SHOULD be present.
- `Offer: draw` is only meaningful with `Action: move`, mirroring
  over-the-board practice where a draw is offered together with a move.

Unknown headers MUST be ignored (forward compatibility). Unknown `Action`
values MUST cause rejection with an explanation to the user.

## 5. The GameID tag

Every game carries a `[GameID "<uuid4>"]` PGN tag, generated at game
creation and immutable for the life of the game. It lives in the PGN rather
than in a block header so that an exported `.pgn` file alone remains a
complete, routable record. Applications route inbound messages to the local
game whose GameID matches. A message whose GameID is unknown is offered to
the user as a new game, which is how a game invitation works with no extra
machinery.

Display and email subjects use the first eight hex characters as a short
form, for example `5f3a9c2e`.

## 6. Parsing rules

1. Scan the pasted text for the BEGIN line. Match after stripping leading
   whitespace and any leading run of `>` quote markers, so a block copied
   out of a quoted reply still parses.
2. Verify the version token. An unknown version is rejected with an
   explanation, never guessed at.
3. Read headers until the first blank line; everything from there to the
   END line is the PGN.
4. Replay the PGN with a real rules engine. Every move MUST be legal from
   the initial position. A PGN that fails replay is rejected.
5. Validation against local state, when the GameID is known:
   - the local move list MUST be a strict prefix of (or equal to, for
     `draw-accept` and `resign`) the inbound move list, compared move by
     move after parsing, never as text;
   - after import it MUST be the recipient's turn or the game MUST be over;
   - a violation is reported as divergence and local state is not mutated.
6. Senders MUST be conservative: emit exactly the format above with PGN
   movetext lines wrapped at or below 72 characters so mail clients do not
   re-wrap them. Receivers SHOULD be liberal within the rules above, for
   example accepting a multi-move extension after a missed email, provided
   every added move replays legally.

## 7. Fallback for app-less opponents

An opponent without the application sees the preamble and replies in plain
text, for example `Nf6` or `14... Nf6`. This is outside the wire format:
the application accepts a bare SAN move on import as a convenience, applied
to a game the user selects, validated by the same rules engine.

## 8. Subject line convention (non-normative)

`[Postal Gambit <short-id>] move <n>: <SAN>` for moves, with `invitation`,
`draw accepted` or `resignation` in place of the move part where relevant.
The stable bracketed prefix keeps games searchable in any mail client.
Parsers MUST NOT rely on the subject.
