"""
Relais Tk de l'hôte DPI (interfaces/desktop/dpi_host.py) : widgets Tk au lieu
de handles et de rectangles, pour artifacts_panel.py et _edge_embed.py, jusqu'au
retrait de Tk.
"""

from interfaces.desktop import dpi_host as _host


def is_dpi_virtualized(widget) -> bool:
    """True si le widget vit dans une fenêtre que Windows met à l'échelle en bitmap."""
    try:
        return _host.is_dpi_virtualized(int(widget.winfo_id()))
    except (AttributeError, ValueError):
        return False


class DpiAwareHost(_host.DpiAwareHost):
    """Hôte DPI par écran possédé par la fenêtre du widget, posé sur un widget."""

    def __init__(self, owner_widget, background: str = "#111111"):
        """
        Args:
            owner_widget: Widget de la fenêtre principale (sa racine possède l'hôte).
            background: Couleur de fond, visible le temps du chargement.
        """
        try:
            owner = int(owner_widget.winfo_toplevel().wm_frame(), 16)
        except (AttributeError, ValueError):
            owner = 0
        super().__init__(owner, background)

    def place_over(self, widget, show: bool = True) -> None:
        """Aligne l'hôte, en pixels physiques, sur le rectangle écran du widget."""
        rect = _host.screen_rect(int(widget.winfo_id()))
        if rect is not None:
            self.place(rect, show)
