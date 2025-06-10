import random
import uuid
import flet as ft

# ──────────────────────────────────────────────────────────────
#  Online Tic‑Tac‑Toe (3‑piece variant) using Flet pub‑sub 
#  Join the same room URL (e.g. /room42) to play together.
# ──────────────────────────────────────────────────────────────

GAMES: dict[str, "GameState"] = {}  # room_id ➜ GameState

class GameState:  # Server‑side state container ----------------------------
    def __init__(self):
        self.board: list[str | None] = [None] * 9            # 3×3 board
        self.pieces: dict[str, list[int]] = {"X": [], "O": []}
        self.current: str = "X"                              # whose turn
        self.winner: str | None = None                       # "X" or "O"
        self.players: dict[str, str] = {}                    # session_key ➜ symbol

    def _wins(self, p: str) -> bool:  # check 3‑in‑a‑row
        w = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),
             (1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        return any(all(self.board[i] == p for i in tri) for tri in w)

    def move(self, p: str, idx: int) -> bool:
        if self.winner or self.board[idx] is not None or p != self.current:
            return False
        if len(self.pieces[p]) == 3:  # Already 3 pieces → remove one at random
            rem = random.choice(self.pieces[p])
            self.board[rem] = None
            self.pieces[p].remove(rem)
        self.board[idx] = p
        self.pieces[p].append(idx)
        if self._wins(p):
            self.winner = p
        else:
            self.current = "O" if p == "X" else "X"
        return True

    def reset(self):
        self.__init__()

# ——————————————————— Flet UI ————————————————————————————————

def main(page: ft.Page):
    room_id = page.route.lstrip("/") or "default"
    game = GAMES.setdefault(room_id, GameState())

    sk = str(uuid.uuid4()) 

    if sk not in game.players:
        taken = set(game.players.values())
        game.players[sk] = "X" if "X" not in taken else ("O" if "O" not in taken else "Spectator")
    symbol = game.players[sk]

    page.title = f"Tic‑Tac‑Toe • Room {room_id}"
    page.horizontal_alignment = "center"
    page.vertical_alignment = "center"
    page.window_width, page.window_height = 380, 580

    info = ft.Text(f"You are: {symbol}", size=14)
    status = ft.Text(size=18, weight="bold")
    cells: list[ft.ElevatedButton] = []

    def broadcast():
        page.pubsub.send_all({"room": room_id, "type": "sync"})

    def refresh():
        for i, btn in enumerate(cells):
            btn.text = game.board[i] or ""
            btn.disabled = (
                game.board[i] is not None or
                symbol != game.current or
                game.winner is not None or
                symbol == "Spectator"
            )
        if game.winner:
            status.value = ("You win! 🎉" if game.winner == symbol else f"Player {game.winner} wins.")
        else:
            if symbol == "Spectator":
                status.value = f"Spectating — Player {game.current} to move"
            elif symbol == game.current:
                status.value = "Your turn"
            else:
                status.value = "Waiting for opponent…"
        page.update()

    def handle_click(e: ft.ControlEvent):
        idx = int(e.control.data)
        if game.move(symbol, idx):
            broadcast()
        refresh()

    for i in range(9):
        cells.append(ft.ElevatedButton(
            text="",
            data=i,
            width=100, height=100,
            on_click=handle_click,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=0),
                padding=0,
                elevation=2
            )
        ))

    reset_btn = ft.FilledButton("Reset game", visible=(symbol == "X"))
    def reset_game(e):
        game.reset()
        broadcast()
        refresh()
    reset_btn.on_click = reset_game

    page.add(
        info, status, ft.Divider(height=8, color="transparent"),
        ft.Column([
            ft.Row(cells[0:3], alignment="center"),
            ft.Row(cells[3:6], alignment="center"),
            ft.Row(cells[6:9], alignment="center"),
        ], spacing=5, alignment="center"),
        reset_btn
    )

    def on_pub(msg):
        if msg.get("room") == room_id and msg.get("type") == "sync":
            refresh()
    page.pubsub.subscribe(on_pub)

    refresh()

if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER, port=8550)
