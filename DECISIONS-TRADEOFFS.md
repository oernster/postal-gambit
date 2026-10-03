# Decisions and trade-offs

The deliberate choices Postal Gambit rests on: what was chosen, what was given
up for it and why. Each entry is the decision as the product makes it today.
The detail behind each one, with the tests that hold it, lives in
[ARCHITECTURE.md](ARCHITECTURE.md) and the email contract in
[WIRE_FORMAT.md](WIRE_FORMAT.md); [TESTING.md](TESTING.md) describes the gate
and [TECH_DEBT.md](TECH_DEBT.md) records what only looks like debt.

## The product as a whole

### The player's own mail client is the transport

Postal Gambit never sends or receives mail. A move becomes a ready-written
email for the player's own mail client to send. It can also go to the
clipboard, to be pasted wherever the player writes mail.

- **Rather than:** a built-in IMAP and SMTP client; a central server.
- **Gains:** no credentials, no sign-in, no polling and no server to run; the
  mail client the player already trusts does the delivering.
- **Costs:** the application cannot see a move arrive. Every reply has to be
  pasted in or opened from its link.

### Python and PySide6

The application is written in Python on Qt for Python widgets.

- **Rather than:** Go with Wails. Its advantage lay in mail plumbing, which
  went away with the decision above; a web application.
- **Gains:** the delivery recipe already proved on earlier projects
  (Nuitka, a bespoke installer, Flatpak, a DMG and the keyboard model).
- **Costs:** a larger runtime than a native binary; packaging takes care.

### No engine, ever

The application enforces the rules and nothing more. It suggests no move,
evaluates no position and ships no engine.

- **Rather than:** an optional analysis mode.
- **Gains:** the product is human correspondence chess; "no machines" is the
  scope rather than a default somebody can switch off.
- **Costs:** a player who wants analysis needs another tool.

### An opponent does not need the application

Every email carries a readable preamble and a plain board diagram above the
block. A reply of a bare move such as Nf6 imports against a game the player
chooses.

- **Rather than:** a format only the application can read.
- **Gains:** a game can start with anyone who has an email address.
- **Costs:** a bare move carries no game identity, so the player has to say
  which game it belongs to.

## Privacy and the network

### One disclosed call and no other

The application reaches the network in exactly one way: an anonymous request
to GitHub asking whether a newer published release exists. Games and moves
never touch the network.

- **Rather than:** no update check at all; a library free to reach out
  wherever it likes.
- **Gains:** a player learns of new releases without the claim about their
  games being weakened.
- **Costs:** "no network code" became "no network code bar one named
  module", which has to be disclosed and defended.

### The claim is a test over everything that ships

A structural test fails the suite when a network import appears anywhere in
the package, either composition root or the setup program. The update
check's module is the one exemption; the test also asserts that it ships,
that it still needs the exemption and that it imports nothing more. The scan
asserts its own reach, so narrowing it fails rather than passing quietly.

- **Rather than:** scanning the package alone, which a network call in the
  setup program or the entry point would have passed untouched.
- **Gains:** the product's central claim is a test result about what a user
  installs.
- **Costs:** every new outward feature has to argue with a failing test.

### The build scripts sit outside that claim

The scripts that build the packages are exempt from the network scan by
name, because they fetch wheels and talk to Apple to notarise.

- **Rather than:** holding them to the application's rule.
- **Gains:** the claim stays about what ships rather than about how it is
  made.
- **Costs:** the exemption is a list to keep honest; it is asserted so it
  cannot grow quietly.

### Update checks: quiet unless there is news

A check runs shortly after launch and then once a day on a background
thread. It says nothing unless a newer release exists; a check from the Help
menu always answers. A version it cannot read is never treated as newer.
Download hands the release address to the browser; Skip this version is
remembered for the automatic checks only.

- **Rather than:** a check that reports every outcome; downloading or
  installing on the player's behalf.
- **Gains:** updates are found without nagging; nothing is fetched or run
  without a press.
- **Costs:** one unprompted request a day; the Linux package has to be
  granted network access for that one request.

### Donations go through the browser

The donate button hands its address to the desktop and the browser does the
asking. The address has one home in the source, leaves through one seam and
is pinned by a structural test.

- **Rather than:** opening the payment page from inside the application.
- **Gains:** the button opens no connection of its own, so the network claim
  is untouched.
- **Costs:** none recorded.

## The email and its contract

### The game travels as PGN, whole, in every email

The block carries the complete game from move one, never just the latest
move. Whose turn it is, the status and the result are always worked out from
that PGN by replay.

- **Rather than:** sending deltas; storing turn and status beside the game.
- **Gains:** a lost or out-of-order email cannot corrupt a game; the latest
  message always suffices. There is one source of truth to drift from.
- **Costs:** every email grows with the game; each read replays it.

### A plain text block between two delimiter lines

The game sits in a block between BEGIN and END lines, in the style of a PEM
certificate, with a version in the BEGIN line. It is found even inside a
quoted reply.

- **Rather than:** an attachment, which a mailto link cannot carry; a JSON
  payload, which is hostile to an opponent without the application; bare PGN,
  which cannot say "I resign" or "I accept the draw".
- **Gains:** the block survives pasting and quoting in any mail client and
  says what the message does.
- **Costs:** it is visible text in the email, which some readers will find
  odd.

### Wire format v1 is frozen

The block's format is frozen at version 1. A breaking change would bump the
token in the BEGIN line and get a parser of its own; a version the parser
does not know is refused rather than guessed at. The format's version does
not follow the application's.

- **Rather than:** a format that moves with each release; no version at all.
- **Gains:** a game played over months survives the two players running
  different releases, since the block is the only thing their copies share.
- **Costs:** improvements to the block wait for a reason good enough to
  break it.

### Unknown headers are ignored

A header the parser does not recognise is skipped. That is how the optional
From header, carrying the sender's address, was added without a new version.

- **Rather than:** rejecting anything unrecognised.
- **Gains:** additions within v1 reach older copies harmlessly.
- **Costs:** a mistyped header is silently ignored rather than reported.

### The sender's address is a convenience, never an identity

A game created from an invitation or a first move takes the opponent's
address from the From header. It is shown before the game is created. Where
the header is missing the player is asked.

- **Rather than:** asking for the address every time; carrying it in the
  link.
- **Gains:** a game started from a one-click link needs nothing typed.
- **Costs:** anyone can write any address there, so it is treated as a
  suggestion to confirm.

### Generous on import; divergence is reported, never resolved

An import is accepted when the local moves are a strict prefix of the
inbound ones and every added move is legal, so a missed email is recovered
by the next one. Anything else is reported as divergence and the local game
is left as it was.

- **Rather than:** accepting exactly one new move; resolving a conflict
  automatically.
- **Gains:** a lost email costs nothing; a disagreement is never settled
  behind the player's back.
- **Costs:** a real divergence is the players' to sort out by hand.

### A board diagram in plain letters

The email shows the position as letters on a grid, with file letters and
rank numbers round it.

- **Rather than:** Unicode chess pieces; HTML mail.
- **Gains:** it reads the same in every client and font.
- **Costs:** it is plainer to look at than a picture of a board.

### Each game has a permanent identity in its PGN

A game is named by a random identifier held as a tag in its PGN. A short
form of it appears in every email subject and in every game's name in the
list.

- **Rather than:** the identity in a header of the block only; an identity
  made from the players and the date.
- **Gains:** an exported PGN file is a complete, routable record on its own;
  a list row and its email thread can be matched at a glance.
- **Costs:** every name carries a short code.

### A one-click link that degrades to the paste

Every email also carries an https link whose fragment holds the compressed
block. A static page on the project site turns it into a postalgambit link
and hands it to the installed application, which opens the import dialog
filled in. The same validation and the same Import press apply as for a
paste.

- **Rather than:** a bare postalgambit link, which mail clients leave as
  inert text; a link that imports without asking.
- **Gains:** one click in any mail client; the fragment never reaches a
  server, so the game stays between the players.
- **Costs:** the emitted address has to keep resolving for as long as any
  email carrying it exists; a client that strips links loses only the
  shortcut.

## Playing a game

### Playing a move sends nothing

A move updates the board and waits. Send move writes the email when the
player asks for it.

- **Rather than:** opening the email the moment a move is played.
- **Gains:** nothing covers the board at the moment its new position is
  worth looking at.
- **Costs:** one more press per move.

### A move can be taken back until its email leaves

A move can be undone until its email is handed to the mail client or the
clipboard, the last step the application can see. After that it is final.
Send and Take back are answered by one question, so they light and grey
together. Every other change to a game (a resignation, an accepted draw, an
imported reply) also settles the waiting move; a game saved before this
existed reads as sent.

- **Rather than:** no take-back; take-back at any time; each action clearing
  the waiting move only when it remembers to.
- **Gains:** a slip is free to correct while the opponent cannot have seen
  it; a stale waiting move cannot linger and silence is read the safe way.
- **Costs:** the application cannot tell whether the player really pressed
  send in their mail client; once the email has left, re-sending it is not
  offered.

### A draw offer rides on the move

A draw is offered together with a move, as over the board. The offer is kept
with the waiting move, survives the send and goes when the move is taken
back.

- **Rather than:** an offer on its own; an offer held only on a checkbox,
  which a later send would have dropped.
- **Gains:** sending the same move again says the same thing.
- **Costs:** none recorded.

### The player's colour is a decision

The New game dialog starts with neither colour chosen. Its OK stays
unavailable until a name, an address containing an at sign and a colour are
given.

- **Rather than:** a default colour that could be overlooked.
- **Gains:** a game never starts on the wrong side by accident.
- **Costs:** one more choice on every new game.

### Actions work across a selection

Resign, accept draw, delete, take back and send apply to every selected game
they fit, after one confirmation that names the games. Each ended game still
gets its own email, since each opponent is owed one.

- **Rather than:** one game at a time.
- **Gains:** a player with many games can act on them together.
- **Costs:** several email dialogs in a row after a bulk resignation.

## Storage and the mail hand-off

### One JSON file per game, written atomically

Each game is one versioned JSON document in a folder under the home
directory, written to a temporary file and moved into place.

- **Rather than:** SQLite, whose relational shape is not needed; one large
  file for every game.
- **Gains:** files that can be read, copied and backed up by hand; a crash
  mid-write leaves the old game intact.
- **Costs:** no queries across games; the application is the only safe
  writer.

### The mail client is reached the way each platform honours

On Windows the mailto link goes through the same shell path a clicked link
uses. On Linux it goes to the desktop opener exactly as encoded. On macOS
Qt's own opener is used. A link too long for some clients and shells to
carry whole is not offered; the dialog steers to the clipboard instead.

- **Rather than:** Qt's opener everywhere. On Windows it can follow a stale
  registry entry to the wrong mail client; on Linux it re-encodes the text
  and mangles the email. Handing over a link that may arrive truncated.
- **Gains:** the player's actual default mail client opens with the email
  intact; a long game never arrives cut short.
- **Costs:** three code paths for one action; a long game needs a paste
  rather than one press.

## The interface

### The whole application works from the keyboard

Every control is on one explicit focus ring, dialogs included; Enter and
Space both activate whatever has focus. On the board all four arrows move a
square cursor and only Tab leaves it.

- **Rather than:** mouse-first controls; the toolkit's default behaviour,
  under which Space did nothing in menus on Windows.
- **Gains:** a whole game can be played without a mouse.
- **Costs:** every new control needs its place in the ring.

### A focus ring belongs to a control, never to a pane

Buttons ring on hover and on focus; fields and choices ring on focus. A list
shows its current row instead of a ring round the whole box. A read-only text
region is a stop only while it overflows. Two structural tests hold this,
one reading the built stylesheet and one walking the real focus chain.

- **Rather than:** rings drawn round lists and panes, which outlined
  everything while selecting nothing.
- **Gains:** where focus is always shows on something that can be acted on.
- **Costs:** a list that refreshes has to put its current row back by hand.

### A disabled control wears a red ring

A control that cannot be used shows a permanent red ring over a muted fill,
in both themes.

- **Rather than:** a greyed control that melts into the surface; a ring only
  on hover, which Qt's stylesheets cannot express.
- **Gains:** a dead control is visible as dead.
- **Costs:** more red on screen when little is available.

### One home for every colour

Every colour is a named token in one dark set and one light set; widget code
never names a colour. The board takes its tokens by injection. Dark is the
default; the choice is remembered.

- **Rather than:** Qt palettes; colours written where they are used.
- **Gains:** a theme is one set of values; the two stay consistent.
- **Costs:** a new colour has to earn a token in both sets.

### One copy runs

A second launch, including one started by a clicked link, hands its command
line to the running window over a local socket and exits.

- **Rather than:** several copies writing the same games.
- **Gains:** one writer for the game files; a clicked link lands in the
  window already open.
- **Costs:** the local socket pulls in Qt's networking library, whose
  dependencies the Linux package has to supply.

### The donate button has a strip of its own

The button sits first on a strip along the foot of the window, apart from
every other control, drawn at the height of a real pill button.

- **Rather than:** a seat among the game controls.
- **Gains:** it belongs to nothing on screen, so nothing else is pressed by
  accident.
- **Costs:** a strip of height given to one button.

## Building and installing

### Installed for one user, without administrator rights

The Windows setup program installs into the user's own folders and registry,
registers the postalgambit link scheme there and offers to close a running
copy first.

- **Rather than:** a machine-wide install.
- **Gains:** no administrator prompt.
- **Costs:** each account on a machine installs separately.

### A setup program built like the application

The setup program is split into Qt-free operations and state plus a Qt
window; the first two sit under the full coverage gate. Every external
command, registry location and folder is injected, so tests write to scratch
keys and temporary folders. Every file in the payload is checked to land
inside the install folder before it is written.

- **Rather than:** one large module outside the gate, as it once was.
- **Gains:** the most privileged code in the product is the best measured.
- **Costs:** the setup program is Postal Gambit's own to maintain.

### The running copy is ended by name alone

Closing a running copy ends that program and nothing else; a test pins that
the whole-tree option is absent.

- **Rather than:** ending the whole process tree, which could take the setup
  program down with it and leave no error behind.
- **Gains:** the setup program never vanishes mid-install.
- **Costs:** none recorded; the application starts no children.

### A failed launch is said, not assumed

When asked to start Postal Gambit after installing, the setup program reports
whether it actually started and stays open to say so when it did not.

- **Rather than:** closing on a launch that never happened.
- **Gains:** a silent failure cannot look like success.
- **Costs:** none recorded.

### Uninstalling keeps the games

Removing Postal Gambit keeps the player's games and settings unless a box
asking otherwise is ticked.

- **Rather than:** removing everything.
- **Gains:** a reinstall finds every game where it was.
- **Costs:** a full clean-up needs the box ticked.

### macOS builds are notarised or not released

The macOS build signs and notarises both the application and the disk image
and fails when it cannot. Skipping that is an explicit setting for local test
builds only.

- **Rather than:** shipping a signed but unnotarised build, which Gatekeeper
  rejects.
- **Gains:** a published disk image opens on every Mac.
- **Costs:** an Apple developer account and a stored credential.

### Packages are compiled with a chosen Nuitka or not at all

Every build that compiles with Nuitka first asks the interpreter that will
compile which release it has; it stops when there is none or it is older than
the floor pinned in `requirements-dev.txt`.

- **Rather than:** compiling with whatever Nuitka happens to be installed.
- **Gains:** a release is never built by a compiler nobody chose.
- **Costs:** a build machine has to upgrade before it can build at all.

### A website with no dates

The website carries no dates. Its one version number is stamped from the
version file; its stylesheet and script links carry a hash of their content.

- **Rather than:** hand-edited version numbers; plain asset links.
- **Gains:** the site cannot go stale by the calendar; a browser never pairs a
  new page with an old cached stylesheet.
- **Costs:** the stamper has to be run after each version bump.

## Engineering

### Layers that depend inward, with python-chess behind a port

The code is split into domain, application, infrastructure and interface,
each depending only inward, wired together in one composition root. The
domain imports nothing but the standard library and reads no clock. Only one
adapter imports python-chess; only the interface layer imports Qt. Structural
tests hold every boundary.

- **Rather than:** convention alone; using python-chess directly throughout;
  writing the rules by hand.
- **Gains:** the rules about games and the email format can be tested with
  no disk, screen or clock; replacing the chess library would change one
  file.
- **Costs:** more modules and more explicit wiring.

### Complete coverage outside the Qt code

Line and branch coverage must be total over the package outside its Qt code
and over the setup program's Qt-free halves. The interface is outside the
gate.

- **Rather than:** one figure over everything, met only with mocked Qt.
- **Gains:** anything short of complete in the measured code is a decision
  nobody made.
- **Costs:** interface code relies on structural tests and probes.

### Decisions about games live where the gate can see them

Which games an action may be offered for, whether a move promotes a pawn and
where a square sits on the board are answered by the application layer; the
window asks.

- **Rather than:** the window filtering games itself.
- **Gains:** each question has one answer and every answer is measured.
- **Costs:** the window has to ask for things it could have worked out.

### Tests with real parts

No mocking library. Hand-written fakes stand in for the ports; python-chess
is tested as itself; storage uses real files in temporary folders. The
network, size, donate and focus guards were each proved by planting a
violation and watching it fail.

- **Rather than:** mocks and assumed guards.
- **Gains:** a passing test means the real thing works; a guard is known to
  bite.
- **Costs:** fakes are written by hand.

### Small modules and formatting are part of the suite

Every module, the tests included, stays under a size cap with a warning band
below it; a module entering the band is cut back well clear of it rather
than shaved. Formatting and lint run as test assertions. The build scripts
are exempt from the size cap as linear recipes.

- **Rather than:** letting files grow; a separate lint step that can be
  skipped.
- **Gains:** modules split at real seams; a passing suite means formatted
  code.
- **Costs:** many small files; a formatting slip fails the whole run.

### The version lives in one file

The version file is the only place the version is written. The application,
the build scripts and the setup program read it; the site is stamped from it.
The documents quote no test count for the same reason.

- **Rather than:** copies written where they are needed.
- **Gains:** a change is made once and cannot drift.
- **Costs:** static files have to be stamped from the source.
