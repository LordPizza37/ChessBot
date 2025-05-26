import chess
import concurrent.futures
import numpy as np
import concurrent.futures
from evaluate_board import ChessEvaluator
import time
import random
from threading import Lock

# Am Anfang der Datei nach den Imports
_global_evaluator = ChessEvaluator()

PIECE_VALUES = {'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0}

class ChessEnv:
    def __init__(self, player_color, depth, search_time):
        self.search_time = search_time
        self.transposition_table = {}
        self.board = chess.Board()
        self.player_color = player_color
        self.ai_color = not player_color
        self.tt_lock = Lock()
        self.evaluator = ChessEvaluator()  # Erstelle eine einzelne Instanz
        # Erstelle einen neuen Executor für die Instanz
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

    def __del__(self):
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

    global_executor = None

    def reset(self):
        """Setzt das Spiel zurück und gibt den Startzustand zurück."""
        self.board.reset()
        return self.get_state()

    def get_state(self):
        """Gibt den aktuellen Zustand des Bretts als Array zurück."""
        state = np.zeros(64)
        for square, piece in self.board.piece_map().items():
            state[square] = piece.piece_type if piece.color == chess.WHITE else -piece.piece_type
        return state

    def step(self, move):
        """Führt einen Zug aus und gibt neuen Zustand, Belohnung und Spielende zurück."""
        move_obj = chess.Move.from_uci(move)
        if move_obj in self.board.legal_moves:
            self.board.push(move_obj)
            reward = self.get_reward()
            done = self.board.is_game_over()
            return self.get_state(), reward, done
        else:
            return None, -10, True  # Ungültiger Zug gibt hohe Strafe

    def get_reward(self):
        """Belohnung basierend auf Materialvorteil."""
        material_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                           chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
        reward = sum(material_values[piece.piece_type] * (1 if piece.color == chess.WHITE else -1)
                     for piece in self.board.piece_map().values())
        return reward

    def render(self):
        """Zeigt das Brett im Terminal an."""
        print(self.board)

    def get_board_matrix(self):
        """Gibt das Brett OHNE Spiegelung zurück (nur für Weiß korrekt)."""
        board_matrix = [[None] * 8 for _ in range(8)]
        for square, piece in self.board.piece_map().items():
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            board_matrix[rank][file] = piece.symbol()  # Keine Spiegelung!
        return board_matrix

    def get_ai_move(self):
        start_time = time.time()
        best_move = None
        best_score = -float('inf')
        depth = 1
        
        legal_moves = list(self.board.legal_moves)
        if not legal_moves:
            return None

        try:
            while time.time() - start_time < self.search_time * 0.8:  # 80% der verfügbaren Zeit
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(legal_moves))) as executor:
                    current_best_move = None
                    current_best_score = -float('inf')
                    
                    futures = {
                        executor.submit(
                            self.evaluate_move_with_depth,
                            move,
                            depth,
                            start_time
                        ): move for move in legal_moves
                    }
                    
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            move = futures[future]
                            score = future.result(timeout=0.1)
                            
                            if score > current_best_score:
                                current_best_score = score
                                current_best_move = move
                        except Exception as e:
                            print(f"Fehler bei Tiefe {depth}: {e}")
                            continue
                    
                    if current_best_move:
                        best_move = current_best_move
                        best_score = current_best_score
                        
                depth += 1
                
        except concurrent.futures.TimeoutError:
            print(f"Iterative Deepening beendet bei Tiefe {depth-1}")
        
        return best_move or random.choice(legal_moves)

    def evaluate_move_with_depth(self, move, depth, start_time):
        """Bewertet einen Zug mit bestimmter Tiefe."""
        board_copy = self.board.copy()  # Erstelle eine Kopie des Boards
        board_copy.push(move)
        return -minimax(
            board_copy, 
            depth,
            -float('inf'),
            float('inf'),
            self.transposition_table,
            start_time,
            self.search_time
        )

    def evaluate_move(self, move: chess.Move, start_time: float = None) -> float:
        """Bewertet einen Zug mit Minimax und Alpha-Beta-Pruning."""
        if move is None:
            raise TypeError("move darf nicht None sein")
        
        if not hasattr(self, 'search_time'):
            raise AttributeError("search_time muss definiert sein")
        
        if start_time and start_time < 0:
            raise ValueError("start_time muss positiv sein")
        
        current_time = time.time()
        effective_start = start_time if start_time is not None else current_time
        remaining_time = max(0.01, self.search_time - (current_time - effective_start))
        
        try:
            with self.board.copy() as board_copy:
                board_copy.push(move)
                return self._execute_minimax(board_copy, remaining_time)
        except TimeoutError:
            self.logger.warning(f"Zeitüberschreitung bei der Bewertung von Zug {move}")
            return float('-inf')
        except Exception as e:
            self.logger.error(f"Fehler bei der Bewertung von Zug {move}: {str(e)}")
        raise


    def get_move_value(board, move):
        score = 0

        # Priorisiere Schlagzüge nach Materialwert
        if board.is_capture(move):
            captured = board.piece_at(move.to_square)
            score += 1.5 + (captured.piece_type if captured else 0)

        # Priorisiere Checks
        if board.gives_check(move):
            score += 2.5

        # Bestrafe das Zurückziehen in die erste Reihe
        if move.from_square in chess.SquareSet(chess.BB_RANK_1 | chess.BB_RANK_8):
            score -= 2.0

        # Bonus für Zentrumskontrolle
        if chess.square_file(move.to_square) in [3, 4] and chess.square_rank(move.to_square) in [3, 4]:
            score += 2.0

        return score


        MATERIAL_VALUES = np.array([0, 1, 3, 3, 5, 9, 1000])  # [None, P, N, B, R, Q, K]

def minimax(
        board: chess.Board,
        depth: int,
        alpha: float = -float('inf'),
        beta: float = float('inf'),
        transposition_table: dict = None,
        start_time: float = None,
        time_limit: float = None,
        thread_pool: concurrent.futures.ThreadPoolExecutor = None
) -> float:
    """
    Berechnet den besten Zug durch rekursive Simulation aller möglichen Züge.
    Nutzt Alpha-Beta-Pruning, um irrelevante Spielverläufe frühzeitig zu verwerfen.
    """
    if start_time and time.time() - start_time > time_limit:
        return float('-inf')

    if depth == 0 or board.is_game_over():
        return evaluate_position(board)

    moves = list(board.legal_moves)
    moves.sort(key=lambda m: rate_move(board, m), reverse=True)
    
    best_score = -float('inf')

    for move in moves:
        # Prüfe auf schlechte Schlagzüge
        material_change = _global_evaluator.evaluate_material_change(board, move)
        
        board.push(move)
        score = -minimax(board, depth - 1, -beta, -alpha, transposition_table, start_time, time_limit)
        
        # Füge Materialänderungsbewertung hinzu
        score += material_change
        
        board.pop()
        
        best_score = max(best_score, score)
        alpha = max(alpha, score)
        if alpha >= beta:
            break

    return best_score

def rate_move(board: chess.Board, move: chess.Move) -> float:
    """Bewertet einen Zug für Move-Ordering."""
    score = 0.0
    piece = board.piece_at(move.from_square)
    if not piece:
        return score

    # Eröffnungsphase (erste 10 Züge)
    if board.fullmove_number <= 10:
        # Stark erhöhter Bonus für Zentrumsbesetzung mit Bauern
        if piece.piece_type == chess.PAWN:
            if move.to_square in [27, 28, 35, 36]:  # e4, d4, e5, d5
                score += 5.0
            
        # Bestrafung für frühe Damenzüge
        if piece.piece_type == chess.QUEEN:
            score -= 4.0
            
        # Bonus für Entwicklung von Leichtfiguren
        if piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
            # Bonus für Entwicklung vom Startfeld
            if (piece.color == chess.WHITE and chess.square_rank(move.from_square) == 1) or \
               (piece.color == chess.BLACK and chess.square_rank(move.from_square) == 6):
                score += 3.0
                
            # Extra Bonus für Entwicklung ins erweiterte Zentrum
            if move.to_square in [26, 27, 28, 29, 34, 35, 36, 37]:  # c4-f4, c5-f5
                score += 2.0

    # Standardbewertungen für das ganze Spiel
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        if victim:
            score += 10 * victim.piece_type - piece.piece_type

    if board.is_castling(move):
        score += 7.0

    if piece.piece_type == chess.KING and not board.is_castling(move):
        if board.fullmove_number < 40 and len(board.piece_map()) > 10:
            score -= 8.0

    # Verbesserte Rückzugsbewertung
    if board.fullmove_number <= 10:  # Stärkere Bestrafung in der Eröffnung
        if piece.color == chess.WHITE:
            if chess.square_rank(move.to_square) < chess.square_rank(move.from_square):
                score -= 2.0
        else:
            if chess.square_rank(move.to_square) > chess.square_rank(move.from_square):
                score -= 2.0

    return score

def evaluate_position(board: chess.Board) -> float:
    """Erweiterte Stellungsbewertung."""
    base_score = _global_evaluator.evaluate_board(board)
    
    # Zusätzliche Eröffnungsbewertung
    if board.fullmove_number <= 10:
        development_score = 0.0
        
        # Bewerte Entwicklung und Zentrumskontrolle
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                # Zentrumsbonus für Bauern
                if piece.piece_type == chess.PAWN:
                    if square in [27, 28, 35, 36]:  # e4, d4, e5, d5
                        development_score += 0.5 if piece.color == chess.WHITE else -0.5
                
                # Malus für frühe Damenzüge
                elif piece.piece_type == chess.QUEEN:
                    if (piece.color == chess.WHITE and square != chess.D1) or \
                       (piece.color == chess.BLACK and square != chess.D8):
                        development_score -= 0.3 if piece.color == chess.WHITE else -0.3
                
                # Bonus für entwickelte Leichtfiguren
                elif piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                    if (piece.color == chess.WHITE and chess.square_rank(square) > 1) or \
                       (piece.color == chess.BLACK and chess.square_rank(square) < 6):
                        development_score += 0.4 if piece.color == chess.WHITE else -0.4

        base_score += development_score

    multiplier = 1 if board.turn == chess.WHITE else -1
    return base_score * multiplier

def process_move(board, move, depth, alpha, beta, tt, start_time, time_limit):
    board.push(move)
    score = minimax(board, depth - 1, alpha, beta, tt, start_time, time_limit)
    board.pop()
    return score

def quiescence(board: chess.Board, alpha: float, beta: float) -> float:
    """Quiescence Search zur Vermeidung von Horizonteffekten."""
    score = _global_evaluator.evaluate_board(board)
    if not board.turn:  # Für Schwarz negieren
        score = -score
        
    if score >= beta:
        return beta
    alpha = max(alpha, score)

    for move in board.generate_legal_captures():
        board.push(move)
        eval = -quiescence(board, -beta, -alpha)
        board.pop()

        if eval >= beta:
            return beta
        alpha = max(alpha, eval)

    return alpha

