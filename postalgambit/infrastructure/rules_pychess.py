"""RulesEngine adapter over python-chess: the only module importing it."""

from __future__ import annotations

import io
from typing import Mapping

import chess
import chess.pgn

from postalgambit.application.dto import (
    RESULT_ONGOING,
    BoardView,
    GameStatus,
    MoveApplied,
)
from postalgambit.domain.errors import IllegalMoveError, IllegalPgnError
from postalgambit.domain.game import Colour

PGN_EXPORT_COLUMNS = 72
STATUS_IN_PROGRESS = "in progress"
STATUS_FINISHED = "finished"

_PROMOTION_PIECES = {
    "q": chess.QUEEN,
    "r": chess.ROOK,
    "b": chess.BISHOP,
    "n": chess.KNIGHT,
}

_TERMINATION_PHRASES = {
    chess.Termination.CHECKMATE: "checkmate",
    chess.Termination.STALEMATE: "stalemate",
    chess.Termination.INSUFFICIENT_MATERIAL: "insufficient material",
    chess.Termination.SEVENTYFIVE_MOVES: "seventy-five-move rule",
    chess.Termination.FIVEFOLD_REPETITION: "fivefold repetition",
}

_COLOUR_LABELS = {True: "White", False: "Black"}


class PythonChessRulesEngine:
    """Stateless adapter; every method replays the given PGN."""

    def validate(self, pgn: str) -> None:
        self._read(pgn)

    def normalize(self, pgn: str) -> str:
        return self._export(self._read(pgn))

    def moves(self, pgn: str) -> tuple[str, ...]:
        game = self._read(pgn)
        board = game.board()
        sans: list[str] = []
        for move in game.mainline_moves():
            sans.append(board.san(move))
            board.push(move)
        return tuple(sans)

    def turn(self, pgn: str) -> Colour:
        board = self._final_board(self._read(pgn))
        return Colour.WHITE if board.turn == chess.WHITE else Colour.BLACK

    def status(self, pgn: str) -> GameStatus:
        game = self._read(pgn)
        return self._status_of(game, self._final_board(game))

    def headers(self, pgn: str) -> Mapping[str, str]:
        return dict(self._read(pgn).headers)

    def board_view(self, pgn: str) -> BoardView:
        board = self._final_board(self._read(pgn))
        squares: list[str] = []
        for rank in range(7, -1, -1):
            for file in range(8):
                piece = board.piece_at(chess.square(file, rank))
                squares.append(piece.symbol() if piece else "")
        return BoardView(
            squares=tuple(squares),
            turn=Colour.WHITE if board.turn == chess.WHITE else Colour.BLACK,
            in_check=board.is_check(),
        )

    def ascii_board(self, pgn: str) -> str:
        board = self._final_board(self._read(pgn))
        files_label = "  a b c d e f g h"
        rows = [files_label]
        for offset, row in enumerate(str(board).splitlines()):
            rank = 8 - offset
            rows.append(f"{rank} {row} {rank}")
        rows.append(files_label)
        return "\n".join(rows)

    def legal_targets(self, pgn: str, source: str) -> tuple[str, ...]:
        board = self._final_board(self._read(pgn))
        square = self._parse_square(source)
        targets = {
            chess.square_name(move.to_square)
            for move in board.legal_moves
            if move.from_square == square
        }
        return tuple(sorted(targets))

    def apply_uci(
        self, pgn: str, source: str, target: str, promotion: str | None = None
    ) -> MoveApplied:
        game = self._read(pgn)
        board = self._final_board(game)
        move = chess.Move(
            self._parse_square(source),
            self._parse_square(target),
            promotion=self._parse_promotion(promotion),
        )
        if move not in board.legal_moves:
            raise IllegalMoveError(f"illegal move {source}-{target}")
        return self._push(game, board, move)

    def apply_san(self, pgn: str, san: str) -> MoveApplied:
        game = self._read(pgn)
        board = self._final_board(game)
        try:
            move = board.parse_san(san)
        except ValueError:
            raise IllegalMoveError(f"illegal move {san!r}") from None
        return self._push(game, board, move)

    def with_result(self, pgn: str, result: str, termination: str) -> str:
        game = self._read(pgn)
        game.headers["Result"] = result
        game.headers["Termination"] = termination
        return self._export(game)

    def _read(self, pgn: str) -> chess.pgn.Game:
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            raise IllegalPgnError("no PGN game found")
        if game.errors:
            raise IllegalPgnError(f"PGN failed to replay: {game.errors[0]}")
        return game

    def _final_board(self, game: chess.pgn.Game) -> chess.Board:
        return game.end().board()

    def _parse_square(self, name: str) -> chess.Square:
        try:
            return chess.parse_square(name.lower())
        except ValueError:
            raise IllegalMoveError(f"not a square: {name!r}") from None

    def _parse_promotion(self, promotion: str | None) -> chess.PieceType | None:
        if promotion is None:
            return None
        piece = _PROMOTION_PIECES.get(promotion.lower())
        if piece is None:
            raise IllegalMoveError(f"not a promotion piece: {promotion!r}")
        return piece

    def _push(
        self, game: chess.pgn.Game, board: chess.Board, move: chess.Move
    ) -> MoveApplied:
        san = board.san(move)
        mover = Colour.WHITE if board.turn == chess.WHITE else Colour.BLACK
        move_number = board.fullmove_number
        game.end().add_main_variation(move)
        board.push(move)
        outcome = board.outcome()
        if outcome is not None:
            game.headers["Result"] = outcome.result()
        new_pgn = self._export(game)
        return MoveApplied(
            new_pgn=new_pgn,
            san=san,
            move_number=move_number,
            mover=mover,
            status=self._status_of(game, board),
        )

    def _status_of(self, game: chess.pgn.Game, board: chess.Board) -> GameStatus:
        outcome = board.outcome()
        if outcome is not None:
            phrase = _TERMINATION_PHRASES[outcome.termination]
            if outcome.winner is None:
                description = f"{phrase}, draw"
            else:
                description = f"{phrase}, {_COLOUR_LABELS[outcome.winner]} wins"
            return GameStatus(result=outcome.result(), description=description)
        result = game.headers.get("Result", RESULT_ONGOING)
        if result == RESULT_ONGOING:
            return GameStatus(result=result, description=STATUS_IN_PROGRESS)
        phrase = game.headers.get("Termination", STATUS_FINISHED)
        if result.endswith("-0"):
            return GameStatus(result=result, description=f"{phrase}, White wins")
        if result.startswith("0-"):
            return GameStatus(result=result, description=f"{phrase}, Black wins")
        return GameStatus(result=result, description=phrase)

    def _export(self, game: chess.pgn.Game) -> str:
        exporter = chess.pgn.StringExporter(
            headers=True,
            variations=False,
            comments=False,
            columns=PGN_EXPORT_COLUMNS,
        )
        return game.accept(exporter)
