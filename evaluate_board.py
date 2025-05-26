from dataclasses import dataclass
import chess
from typing import Dict, Optional

@dataclass
class PositionalConstants:
    CENTRAL_PAWN_BONUS: float = 0.3
    CENTRAL_KNIGHT_BONUS: float = 0.5
    DOUBLED_PAWN_PENALTY: float = 0.5
    KING_SAFETY_PENALTY: float = 0.3
    CHECKMATE_BONUS: float = 1000.0
    FIELD_CONTROL_BONUS: float = 0.1
    MINOR_PIECE_DEVELOPMENT_BONUS: float = 0.1
    MAJOR_PIECE_ACTIVITY_BONUS: float = 0.2
    PAWN_STRUCTURE_BONUS: float = 0.1

class ChessEvaluator:
    def __init__(self):
        # Grundlegende Materialwerte
        """
        Materialwerte und positionsbasierte Boni für die KI-Bewertung.
        - Weiße Figuren: Positive Werte
        - Schwarze Figuren: Negative Werte
        """
        self.piece_values = {
            'P': 100,    # Bauer
            'N': 320,    # Springer
            'B': 330,    # Läufer
            'R': 500,    # Turm
            'Q': 900,    # Dame
            'K': 20000,  # König
            'p': -100,
            'n': -320,
            'b': -330,
            'r': -500,
            'q': -900,
            'k': -20000
        }
        
        # Positionelle Boni (maximal 10% des Figurenwerts)
        self.positional_bonus = {
            chess.PAWN: 10,     # 10% von 100
            chess.KNIGHT: 32,   # 10% von 320
            chess.BISHOP: 33,   # 10% von 330
            chess.ROOK: 50,     # 10% von 500
            chess.QUEEN: 90,    # 10% von 900
            chess.KING: 20      # Kleiner Bonus für König
        }

    def evaluate_board(self, board: chess.Board) -> float:
        """Bewertet das Schachbrett und gibt eine Bewertung zurück."""
        if board.is_checkmate():
            return -20000 if board.turn else 20000
            
        if board.is_stalemate() or board.is_insufficient_material():
            return 0.0
            
        score = self.evaluate_material(board)
        score += self.evaluate_position(board)
        
        return score

    def evaluate_material(self, board: chess.Board) -> float:
        """Bewertet nur das Material auf dem Brett."""
        return sum(self.piece_values[p.symbol()] for p in board.piece_map().values())

    def evaluate_position(self, board: chess.Board) -> float:
        """Bewertet die Position der Figuren."""
        score = 0.0
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if not piece:
                continue
                
            bonus = 0.0
            rank = chess.square_rank(square)
            file = chess.square_file(square)
            
            if board.fullmove_number <= 10:  # Eröffnungsphase
                if piece.piece_type == chess.PAWN:
                    # Zentrumsbonus für Bauern
                    if 2 <= file <= 5 and 3 <= rank <= 4:
                        bonus = self.positional_bonus[chess.PAWN] * 0.5
                        
                elif piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                    # Entwicklungsbonus
                    if (piece.color == chess.WHITE and rank > 0) or \
                       (piece.color == chess.BLACK and rank < 7):
                        bonus = self.positional_bonus[piece.piece_type] * 0.3
                        
                elif piece.piece_type == chess.QUEEN:
                    # Bestrafung für frühe Damenzüge
                    if (piece.color == chess.WHITE and square != chess.D1) or \
                       (piece.color == chess.BLACK and square != chess.D8):
                        bonus = -self.positional_bonus[chess.QUEEN] * 0.2

            # Addiere/Subtrahiere den Bonus je nach Farbe
            score += bonus if piece.color else -bonus
            
        return score

    def evaluate_material_change(self, board: chess.Board, move: chess.Move) -> float:
        """Bewertet Materialänderungen bei einem Zug."""
        if not board.is_capture(move):
            return 0.0

        moving_piece = board.piece_at(move.from_square)
        captured_piece = board.piece_at(move.to_square)
        
        if not moving_piece or not captured_piece:
            return 0.0

        moving_value = abs(self.piece_values[moving_piece.symbol()])
        captured_value = abs(self.piece_values[captured_piece.symbol()])

        # Wenn der Wert der geschlagenen Figur kleiner ist
        if captured_value < moving_value:
            return -(moving_value - captured_value) * 0.1  # Reduzierte Bestrafung
        
        return (captured_value - moving_value) * 0.1  # Reduzierter Bonus