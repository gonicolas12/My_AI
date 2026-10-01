"""
Tests du défilement de la conversation (interfaces/gui/chat_area.py et
animations.py).

Deux défauts observés en usage réel :
- au-dessus d'une bulle IA, la molette défilait 20 fois moins vite : chaque
  recalcul de hauteur (fin d'écriture, changement de largeur) lui remettait un
  renvoi à 1 unité par cran ;
- pendant l'écriture, le défilement automatique se calait sur le bas du
  contenu : une bulle plus haute que son texte montrait du vide à la place du
  texte en cours.
"""

import sys
import types

import pytest

from interfaces.gui.animations import AnimationsMixin
from interfaces.gui.chat_area import ChatAreaMixin


@pytest.fixture(name="tk_root", scope="module")
def _tk_root():
    """Une seule racine Tk pour le module : en enchaîner plusieurs dans un même
    processus échoue par intermittence sous Windows."""
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("pas d'affichage disponible")
    root.withdraw()
    yield root
    root.destroy()


class _Canvas:
    """Canvas de la conversation : une vue de `height` px sur `content` px
    (yscrollincrement = 1, comme CTkScrollableFrame sous Windows)."""

    def __init__(self, rooty=100, view_top=1000, height=400, content=3000):
        self.rooty, self.view_top, self.height, self.content = rooty, view_top, height, content
        self.scrolled = []

    def __str__(self):
        return ".!ctkframe.!canvas"

    def _move_to(self, top):
        self.view_top = max(0, min(top, self.content - self.height))

    def yview_scroll(self, number, what):
        self.scrolled.append((number, what))
        self._move_to(self.view_top + number)

    def yview_moveto(self, fraction):
        self._move_to(fraction * self.content)

    def yview(self, *args):
        """Commande de la barre de défilement : moveto ou scroll."""
        if args[0] == "moveto":
            self.yview_moveto(float(args[1]))
        else:
            self.yview_scroll(int(args[1]), args[2])

    def bbox(self, _tag):
        return (0, 0, 800, self.content)

    def at_bottom(self):
        self.view_top = self.content - self.height
        return self

    def configure(self, **_options):
        pass

    def update_idletasks(self):
        pass

    def winfo_rooty(self):
        return self.rooty

    def canvasy(self, y):
        return self.view_top + y

    def winfo_height(self):
        return self.height


class _Chat(ChatAreaMixin):
    use_ctk = True

    def __init__(self, canvas):
        self.canvas = canvas
        self.typing_widget = None
        self.scrolls_to_bottom = 0

    def _get_parent_canvas(self):
        return self.canvas

    def scroll_to_bottom(self):
        self.scrolls_to_bottom += 1


class _Wheel:
    def __init__(self, delta=0, num=None):
        self.delta, self.num = delta, num


# ── Molette ─────────────────────────────────────────────────────────────────


@pytest.mark.skipif(sys.platform == "darwin", reason="deltas Windows (120 par cran)")
@pytest.mark.parametrize("event, units", [
    (_Wheel(delta=-120), 20),  # un cran vers le bas
    (_Wheel(delta=240), -40),  # deux crans vers le haut
])
def test_wheel_scrolls_the_chat_at_native_speed(event, units):
    canvas = _Canvas()

    assert _Chat(canvas)._scroll_chat_with_wheel(event) == "break"
    assert canvas.scrolled == [(units, "units")]


@pytest.mark.parametrize("event, units", [(_Wheel(num=4), -20), (_Wheel(num=5), 20)])
def test_linux_wheel_buttons_scroll_the_chat(event, units):
    canvas = _Canvas()
    _Chat(canvas)._scroll_chat_with_wheel(event)

    assert canvas.scrolled == [(units, "units")]


def test_blocked_ai_bubble_scrolls_like_the_rest(tk_root):
    """_disable_text_scroll est réappliqué à chaque recalcul de hauteur : il
    doit renvoyer la molette à la conversation, à sa vitesse (testée ci-dessus)."""
    import tkinter as tk

    widget = tk.Text(tk_root)
    try:
        _Chat(_Canvas())._disable_text_scroll(widget)
        # Molette hors écran non simulable (Windows la livre sous le pointeur) :
        # on vérifie la fonction liée
        bindings = [widget.bind(seq) for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>")]
    finally:
        widget.destroy()

    assert all("_scroll_chat_with_wheel" in script for script in bindings)


# ── Défilement manuel : le suivi s'arrête, puis reprend en bas ─────────────


@pytest.mark.skipif(sys.platform == "darwin", reason="deltas Windows (120 par cran)")
def test_scrolling_up_stops_following():
    chat = _Chat(_Canvas().at_bottom())

    chat._scroll_chat_with_wheel(_Wheel(delta=120))  # un cran vers le haut

    assert chat._follow_chat_bottom is False


@pytest.mark.skipif(sys.platform == "darwin", reason="deltas Windows (120 par cran)")
def test_back_at_the_bottom_follows_again():
    canvas = _Canvas()
    chat = _Chat(canvas)
    chat._follow_chat_bottom = False

    chat._scroll_chat_with_wheel(_Wheel(delta=-120))  # pas encore en bas
    assert chat._follow_chat_bottom is False
    chat._scroll_chat_with_wheel(_Wheel(delta=-120 * 100))  # tout en bas
    assert chat._follow_chat_bottom is True


def test_scrollbar_stops_then_resumes_following():
    chat = _Chat(_Canvas().at_bottom())

    chat._on_chat_scrollbar("moveto", "0.2")
    assert chat._follow_chat_bottom is False
    chat._on_chat_scrollbar("moveto", "1.0")
    assert chat._follow_chat_bottom is True


def test_wheel_elsewhere_in_the_chat_is_noticed():
    """Hors des bulles, CTkScrollableFrame fait défiler ; on constate ensuite."""
    canvas = _Canvas().at_bottom()
    chat = _Chat(canvas)

    canvas.yview_scroll(-60, "units")  # gestionnaire de CTkScrollableFrame
    chat._on_chat_wheel(types.SimpleNamespace(widget=".!ctkframe.!canvas.!frame.!label"))

    assert chat._follow_chat_bottom is False


def test_wheel_outside_the_chat_is_ignored():
    canvas = _Canvas()
    chat = _Chat(canvas)

    chat._on_chat_wheel(types.SimpleNamespace(widget=".!ctkframe.!canvas2"))  # autre zone

    assert chat._follow_chat_bottom is True


def test_writing_leaves_the_reader_in_place():
    canvas = _Canvas(rooty=100, view_top=1000, height=400)
    chat = _Chat(canvas)
    chat.typing_widget = _Bubble(rooty=500, char_box=(8, 100, 9, 20))
    chat._follow_chat_bottom = False

    chat._smart_scroll_follow_animation()
    assert canvas.view_top == 1000
    chat._follow_chat_bottom = True
    chat._smart_scroll_follow_animation()
    assert canvas.view_top != 1000


def test_end_of_answer_leaves_the_reader_in_place():
    canvas = _Canvas(view_top=1000)
    chat = _Chat(canvas)
    chat._follow_chat_bottom = False

    chat._final_smooth_scroll_to_bottom()  # sortie immédiate : pas même de root

    assert canvas.view_top == 1000


def test_automatic_scrolls_skip_a_reader():
    chat = _Chat(_Canvas())
    chat._follow_chat_bottom = False
    chat._scroll_to_bottom_if_following()
    assert chat.scrolls_to_bottom == 0

    chat._follow_chat_bottom = True
    chat._scroll_to_bottom_if_following()
    assert chat.scrolls_to_bottom == 1


def test_new_message_follows_again():
    chat = _Chat(_Canvas())
    chat._follow_chat_bottom = False

    chat._scroll_to_bottom_for_new_turn()

    assert chat._follow_chat_bottom is True
    assert chat.scrolls_to_bottom == 1


# ── Suivi du texte pendant l'écriture ───────────────────────────────────────


class _Bubble:
    """Bulle en cours d'écriture : position à l'écran, boîte du dernier caractère."""

    def __init__(self, rooty, char_box):
        self.rooty, self.char_box = rooty, char_box

    @staticmethod
    def winfo_exists():
        return True

    def winfo_rooty(self):
        return self.rooty

    def bbox(self, _index):
        return self.char_box


def _follow(bubble, canvas, content=(0, 0, 800, 3000)):
    chat = _Chat(canvas)
    chat.typing_widget = bubble
    return chat._typing_follow_fraction(canvas, content)


def test_follow_puts_the_last_character_at_the_bottom_of_the_view():
    # Bulle 400 px sous le haut de la vue (y = 1400 dans le canvas), dernier
    # caractère à y = 100..120 dans la bulle : son bas est à y = 1520
    canvas = _Canvas(rooty=100, view_top=1000, height=400)

    fraction = _follow(_Bubble(rooty=500, char_box=(8, 100, 9, 20)), canvas)

    view_top = 1520 + ChatAreaMixin._FOLLOW_MARGIN_PX - 400
    assert fraction == pytest.approx(view_top / 3000)
    # Le bas du contenu (vide sous le texte) reste hors de la vue
    assert fraction * 3000 + 400 < 3000


def test_unlocatable_character_falls_back_to_the_bottom():
    canvas = _Canvas()

    assert _follow(_Bubble(rooty=500, char_box=None), canvas) == 1.0
    assert _follow(None, canvas) == 1.0


def test_follow_never_goes_above_the_top():
    canvas = _Canvas(rooty=100, view_top=0, height=400)

    assert _follow(_Bubble(rooty=110, char_box=(8, 6, 9, 20)), canvas) == 0.0


# ── Hauteur de la bulle pendant l'écriture ──────────────────────────────────


class _TypingText:
    """Widget Text tel que le lit adjust_text_widget_height."""

    def __init__(self, ypixels, mapped=True):
        self.ypixels, self.mapped = ypixels, mapped
        self.height, self.state = 1, "disabled"

    def winfo_ismapped(self):
        return self.mapped

    def cget(self, option):
        return {"state": self.state, "height": self.height, "font": ("Segoe UI", 12)}[option]

    def configure(self, **options):
        self.height = options.get("height", self.height)
        self.state = options.get("state", self.state)

    def count(self, *_args):
        return self.ypixels  # entier : tkinter ne renvoie un tuple qu'avec une option

    @staticmethod
    def index(_index):
        return "3.0"

    def update_idletasks(self):
        pass


class _Animations(AnimationsMixin):
    _height_adjust_counter = 0
    failed = False

    def _disable_text_scroll(self, _widget):
        self.failed = True  # chemin d'erreur de adjust_text_widget_height


@pytest.mark.usefixtures("tk_root")  # les polices Tk exigent une racine
def test_height_follows_the_measured_text():
    import tkinter.font as tkfont

    widget, animations = _TypingText(ypixels=200), _Animations()
    animations.adjust_text_widget_height(widget)

    line = tkfont.Font(font=("Segoe UI", 12)).metrics("linespace")
    assert not animations.failed
    assert widget.height == -(-(200 + line) // line)
    assert widget.state == "disabled"


@pytest.mark.usefixtures("tk_root")
def test_hidden_bubble_is_not_measured():
    """Fenêtre réduite : la mesure se ferait sur 1 px de large."""
    widget, animations = _TypingText(ypixels=5000, mapped=False), _Animations()
    animations.adjust_text_widget_height(widget)

    assert widget.height == 1
    assert not animations.failed
