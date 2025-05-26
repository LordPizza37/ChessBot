import chess
import pygame
from ChessEnv import ChessEnv
import time
clock = pygame.time.Clock()

# Farbpalette
COLORS = {
    "background": (240, 240, 240),
    "button": (70, 130, 180),
    "button_hover": (100, 150, 200),
    "text": (255, 255, 255),
    "board_light": (238, 238, 210),
    "board_dark": (118, 150, 86)
}

WHITE = (238, 238, 210)
BLACK = (118, 150, 86)

# Fenstergröße
WIDTH, HEIGHT = 800, 800
SQUARE_SIZE = WIDTH // 8


class Button:
    def __init__(self, x, y, width, height, text, radius=10):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.radius = radius
        self.hovered = False

    def draw(self, surface):
        color = COLORS["button_hover"] if self.hovered else COLORS["button"]
        pygame.draw.rect(surface, color, self.rect, border_radius=self.radius)

        font = pygame.font.Font(None, 36)
        text_surf = font.render(self.text, True, COLORS["text"])
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

def load_svg(filename, size):
    """Lädt eine SVG-Datei in pygame und skaliert sie auf die richtige Größe."""
    image = pygame.image.load(filename)  # Lädt die SVG-Datei direkt
    return pygame.transform.scale(image, (size, size))  # Skaliert das Bild auf die Feldgröße



class GUI:
    def __init__(self):
        pygame.init()
        self.clock = pygame.time.Clock()  # Einmalige Instanziierung
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Schach-KI")

        self.game_mode = None  # 'human', 'ai_vs_ai'
        self.player_color = None
        self.search_time = 5
        self.env = None
        self.buttons = []
        self.show_end_screen = False


        self.init_main_menu()

        # Figuren laden
        self.piece_images = {
            piece: pygame.image.load(f"pieces/{'w' if piece.isupper() else 'b'}{piece.upper()}.svg")
            for piece in "PNBRQKpnbrqk"
        }

        self.selected_square = None

        # Falls der Spieler Schwarz ist, muss die KI zuerst ziehen
        if self.player_color == chess.BLACK:
            ai_move = self.env.get_ai_move()
            if ai_move:
                self.env.board.push(ai_move)
                self.ai_moved = True

    def draw_board(self):
        """Zeichnet das Brett mit a1 und h8 immer weiß."""
        for vis_rank in range(8):  # Visuelle Zeile (0 = oben)
            for vis_file in range(8):  # Visuelle Spalte (0 = links)
                # Berechne Originalkoordinaten (unabhängig von der Spielerfarbe)
                if self.player_color == chess.WHITE:
                    original_file = vis_file
                    original_rank = 7 - vis_rank  # Umkehr der Zeile für Weiß-Perspektive
                else:
                    original_file = 7 - vis_file  # Spalten spiegeln
                    original_rank = vis_rank  # Zeilen nicht spiegeln

                # Farbe basierend auf Originalkoordinaten
                color = WHITE if (original_file + original_rank) % 2 == 1 else BLACK

                # Zeichne Feld
                x = vis_file * SQUARE_SIZE
                y = vis_rank * SQUARE_SIZE
                pygame.draw.rect(self.screen, color, (x, y, SQUARE_SIZE, SQUARE_SIZE))

    def draw_pieces(self):
        piece_size = int(SQUARE_SIZE * 0.6)
        offset = (SQUARE_SIZE - piece_size) // 2
        board_matrix = self.env.get_board_matrix()

        for vis_rank in range(8):  # Visuelle Zeile (0 = oben)
            for vis_file in range(8):  # Visuelle Spalte (0 = links)
                # Originalkoordinaten berechnen
                if self.player_color == chess.WHITE:
                    original_rank = 7 - vis_rank
                    original_file = vis_file
                else:
                    original_rank = vis_rank
                    original_file = 7 - vis_file

                piece_symbol = board_matrix[original_rank][original_file]
                if piece_symbol:
                    # Skaliere das Bild
                    piece_image = self.piece_images[piece_symbol]
                    scaled_piece = pygame.transform.scale(piece_image, (piece_size, piece_size))

                    # Zeichne an visueller Position
                    x = vis_file * SQUARE_SIZE + offset
                    y = vis_rank * SQUARE_SIZE + offset
                    self.screen.blit(scaled_piece, (x, y))

    def handle_click(self, pos):
        vis_file = pos[0] // SQUARE_SIZE
        vis_rank = pos[1] // SQUARE_SIZE

        # Korrekte Koordinatenumrechnung
        if self.game_mode == 'human':
            if self.player_color == chess.WHITE:
                original_file = vis_file
                original_rank = 7 - vis_rank
            else:
                original_file = 7 - vis_file
                original_rank = vis_rank
        else:  # Für KI vs KI Modus
            original_file = vis_file
            original_rank = 7 - vis_rank

        square = chess.square(original_file, original_rank)

        if self.selected_square is None:
            # Auswahl einer Figur
            if self.env.board.piece_at(square) and self.env.board.piece_at(square).color == self.player_color:
                self.selected_square = square
        else:
            move = chess.Move(self.selected_square, square)

            # Automatische Promotion zur Dame, falls nicht ausgewählt
            if self.env.board.piece_at(self.selected_square).piece_type == chess.PAWN:
                if (self.player_color == chess.WHITE and chess.square_rank(square) == 7) or \
                        (self.player_color == chess.BLACK and chess.square_rank(square) == 0):
                    move = chess.Move(self.selected_square, square, promotion=chess.QUEEN)

            if move in self.env.board.legal_moves:
                self.env.board.push(move)
                self.ai_moved = False

            self.selected_square = None

            self.draw_board()
            self.draw_pieces()


    def draw_legal_moves(self):
        """Zeichnet die legalen Züge basierend auf der Spielerfarbe."""
        if self.selected_square is not None:
            for move in self.env.board.legal_moves:
                if move.from_square == self.selected_square:
                    # Umrechnung in visuelle Koordinaten
                    to_file = chess.square_file(move.to_square)
                    to_rank = chess.square_rank(move.to_square)

                    # Für Schwarz: Spalten und Zeilen spiegeln
                    if self.player_color == chess.BLACK:
                        to_file = 7 - to_file
                        to_rank = 7 - to_rank

                    # Berechne die Bildschirmposition
                    x = to_file * SQUARE_SIZE
                    y = (7 - to_rank) * SQUARE_SIZE  # Weiß-Perspektive

                    highlight = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                    highlight.fill((255, 0, 0, 100))
                    self.screen.blit(highlight, (x, y))

    def draw_selected_square(self):
        """Zeichnet die Auswahl korrekt gespiegelt."""
        if self.selected_square is not None:
            # Umrechnung in visuelle Koordinaten
            file = chess.square_file(self.selected_square)
            rank = chess.square_rank(self.selected_square)

            # Für Schwarz: Spalten und Zeilen spiegeln
            if self.player_color == chess.BLACK:
                file = 7 - file
                rank = 7 - rank

            # Berechne die Bildschirmposition
            x = file * SQUARE_SIZE
            y = (7 - rank) * SQUARE_SIZE  # Weiß-Perspektive

            pygame.draw.rect(self.screen, (100, 100, 100), (x, y, SQUARE_SIZE, SQUARE_SIZE), 3)

    def handle_promotion(self, from_square, to_square):
        # Ändere den Hintergrund auf die neue Farbe
        self.screen.fill(COLORS["background"])

        # Zeichne Auswahlbuttons
        promo_buttons = [
            Button(200, 300, 150, 50, "Dame (Q)", radius=10),
            Button(400, 300, 150, 50, "Turm (R)", radius=10),
            Button(200, 370, 150, 50, "Läufer (B)", radius=10),
            Button(400, 370, 150, 50, "Springer (N)", radius=10)
        ]

        while True:
            self.screen.fill(COLORS["background"])
            for btn in promo_buttons:
                btn.draw(self.screen)

            pygame.display.flip()

            event = pygame.event.wait()
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, btn in enumerate(promo_buttons):
                    if btn.rect.collidepoint(event.pos):
                        piece_type = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT][i]
                        return chess.Move(from_square, to_square, promotion=piece_type)

    def init_main_menu(self):
        self.buttons = [
            Button(250, 200, 300, 50, "Mensch vs KI", radius=15),
            Button(250, 270, 300, 50, "KI vs KI", radius=15),
            Button(250, 340, 300, 50, f"Rechenzeit: {self.search_time}s", radius=15)
        ]

    def draw_menu(self):
        self.screen.fill(COLORS["background"])
        for btn in self.buttons:
            btn.draw(self.screen)
        pygame.display.flip()

    def handle_menu_events(self):
        """
        Spieler wählt eine Figur aus. Prüft, ob die Figur zur Spielerfarbe gehört.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, btn in enumerate(self.buttons):
                    if btn.rect.collidepoint(event.pos):
                        if i == 0:  # Mensch vs KI
                            self.game_mode = 'human'
                            self.choose_color()
                        elif i == 1:  # KI vs KI
                            self.game_mode = 'ai_vs_ai'
                            self.start_game()
                        elif i == 2:  # Rechenzeit
                            self.search_time = 3 if self.search_time == 5 else 5
                            btn.text = f"Rechenzeit: {self.search_time}s"

            if event.type == pygame.MOUSEMOTION:
                for btn in self.buttons:
                    btn.hovered = btn.rect.collidepoint(event.pos)

    # Angepasste choose_color mit Buttons
    def choose_color(self):
        color_buttons = [
            Button(250, 200, 300, 50, "Weiß spielen", radius=15),
            Button(250, 270, 300, 50, "Schwarz spielen", radius=15),
            Button(250, 340, 300, 50, "Zurück", radius=15)
        ]

        while True:
            self.screen.fill(COLORS["background"])
            for btn in color_buttons:
                btn.draw(self.screen)
            pygame.display.flip()

            event = pygame.event.wait()
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, btn in enumerate(color_buttons):
                    if btn.rect.collidepoint(event.pos):
                        if i == 0:
                            self.player_color = chess.WHITE
                            self.start_game()
                            return
                        elif i == 1:
                            self.player_color = chess.BLACK
                            self.start_game()
                            return
                        elif i == 2:
                            self.init_main_menu()
                            return

            if event.type == pygame.MOUSEMOTION:
                for btn in color_buttons:
                    btn.hovered = btn.rect.collidepoint(event.pos)

    def start_game(self):
        self.env = ChessEnv(None,None,self.search_time,)
        if self.game_mode == 'ai_vs_ai':
            self.player_color = None
            self.env.board = chess.Board()
        else:
            self.env.board = chess.Board()
            if self.player_color == chess.BLACK:
                self.make_ai_move()

        self.selected_square = None
        self.run_game_loop()

    def run_game_loop(self):
        running = True
        while running:
            if self.game_mode == 'ai_vs_ai' or \
                    (self.game_mode == 'human' and self.env.board.turn != self.player_color):

                ai_move = self.env.get_ai_move()
                if ai_move:
                    self.env.board.push(ai_move)
                    print(f"KI-Zug: {ai_move.uci()}")

                    if self.env.board.is_game_over():
                        self.show_end_screen= True
                        running = False

            self.draw_board()
            self.draw_pieces()
            self.draw_legal_moves()
            self.draw_selected_square()

            # Event-Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
                    quit()

                if self.game_mode == 'human' and event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)

            pygame.display.flip()
            self.clock.tick(60)

        if self.show_end_screen:
            self.display_end_screen()  # Umbenennen zur Vermeidung von Rekursion


    def make_ai_move(self):
        ai_move = self.env.get_ai_move()
        if ai_move:
            self.env.board.push(ai_move)
            print(f"KI eröffnet mit: {ai_move.uci()}")

    def display_end_screen(self):
        # Font außerhalb der Schleife initialisieren
        font = pygame.font.Font(None, 50)
        
        # Konstanten definieren
        BUTTON_WIDTH = 300
        BUTTON_HEIGHT = 50
        
        end_buttons = [
            Button((WIDTH - BUTTON_WIDTH) // 2, 300, BUTTON_WIDTH, BUTTON_HEIGHT, "Neues Spiel", radius=15),
            Button((WIDTH - BUTTON_WIDTH) // 2, 370, BUTTON_WIDTH, BUTTON_HEIGHT, "Beenden", radius=15)
        ]
        
        running = True
        while running:
            try:
                self.screen.fill(COLORS["background"])
                result = self.get_game_result()
                text = font.render(result, True, (0, 0, 0))
                self.screen.blit(text, (WIDTH // 2 - text.get_width() // 2, 200))
                
                for btn in end_buttons:
                    btn.draw(self.screen)
                    
                pygame.display.flip()
                
                event = pygame.event.wait()
                if event.type == pygame.QUIT:
                    self.cleanup()
                    running = False
                    
                if event.type == pygame.MOUSEBUTTONDOWN:
                    for i, btn in enumerate(end_buttons):
                        if btn.rect.collidepoint(event.pos):
                            if i == 0:
                                self.init_main_menu()
                                return
                            elif i == 1:
                                self.cleanup()
                                running = False
                                
            except pygame.error as e:
                print(f"Pygame-Fehler aufgetreten: {e}")
                self.cleanup()
                running = False
                
    def cleanup(self):
        """Ressourcen ordnungsgemäß freigeben"""
        try:
            pygame.quit()
        except:
            pass

    def get_game_result(self):
        if self.env.board.is_checkmate():
            if self.env.board.turn == chess.WHITE:
                return "Schwarz gewinnt!"
            else:
                return "Weiß gewinnt!"
        elif self.env.board.is_stalemate():
            return "Unentschieden (Patt)!"
        elif self.env.board.is_insufficient_material():
            return "Unentschieden (Materialmangel)!"
        elif self.env.board.is_seventyfive_moves():
            return "Unentschieden (75 Züge)!"
        elif self.env.board.is_fivefold_repetition():
            return "Unentschieden (5-fache Wiederholung)!"
        else:
            return "Unbekanntes Ergebnis"