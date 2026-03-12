"""
Canvas de workflow visuel style n8n - Nœuds connectés interactifs
Permet de créer des workflows d'agents avec drag & drop, connexions,
zoom, pan, grille et minimap. 100% Python / tkinter.
"""

import math
import tkinter as tk
from typing import Dict, List, Optional, Tuple, Callable, Set


class WorkflowCanvas:
    """Canvas interactif pour workflows visuels d'agents IA (style n8n)."""

    # ── Dimensions ──────────────────────────────────────────────────
    NODE_W = 260
    NODE_H = 110
    PORT_R = 7
    GRID_SIZE = 25
    MINIMAP_W = 160
    MINIMAP_H = 100
    MIN_ZOOM = 0.3
    MAX_ZOOM = 3.0

    # ── Couleurs de statut ──────────────────────────────────────────
    STATUS_META = {
        "idle":    {"color": "#6b7280", "label": "En attente"},
        "running": {"color": "#f59e0b", "label": "En cours"},
        "done":    {"color": "#10b981", "label": "Terminé"},
        "error":   {"color": "#ef4444", "label": "Erreur"},
    }

    # ================================================================
    #  Construction
    # ================================================================

    def __init__(
        self,
        parent,
        colors: dict,
        width: int = 800,
        height: int = 380,
        on_workflow_changed: Optional[Callable] = None,
        snap_to_grid: bool = True,
    ):
        self.parent = parent
        self.colors = colors
        self.on_workflow_changed = on_workflow_changed
        self.snap_to_grid = snap_to_grid

        # ── Données du graphe ───────────────────────────────────────
        self.nodes: Dict[int, dict] = {}
        self.connections: List[dict] = []
        self._next_id = 0

        # ── Sélection ──────────────────────────────────────────────
        self.selected_nodes: Set[int] = set()

        # ── Vue (zoom / pan) ───────────────────────────────────────
        self.zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0

        # ── État d'interaction ─────────────────────────────────────
        self._drag_node_id: Optional[int] = None
        self._drag_off = (0.0, 0.0)
        self._connecting = False
        self._conn_from: Optional[int] = None
        self._conn_line: Optional[int] = None
        self._panning = False
        self._pan_start = (0, 0)
        self._sel_rect: Optional[int] = None
        self._sel_start = (0, 0)

        # ── Widgets ────────────────────────────────────────────────
        self.frame = tk.Frame(parent, bg=colors["bg_secondary"], bd=0,
                              highlightthickness=0)

        self.canvas = tk.Canvas(
            self.frame, width=width, height=height,
            bg=colors["bg_secondary"], highlightthickness=0, relief="flat",
        )
        self.canvas.pack(fill="both", expand=True)

        # Minimap (overlaid)
        self._minimap = tk.Canvas(
            self.frame, width=self.MINIMAP_W, height=self.MINIMAP_H,
            bg="#1a1a1a", highlightthickness=1,
            highlightbackground=colors["border"],
        )
        self._minimap.place(relx=1.0, rely=1.0, anchor="se", x=-8, y=-8)

        # Toolbar légère
        self._create_toolbar()

        self._grid_visible = True

        self._draw_grid()
        self._bind_events()

    # ── Layout helpers ─────────────────────────────────────────────
    def pack(self, **kw):
        """Pack le frame principal. Kwargs passés à pack()."""
        self.frame.pack(**kw)

    def grid(self, **kw):
        """Grid le frame principal. Kwargs passés à grid()."""
        self.frame.grid(**kw)

    def place(self, **kw):
        """Place le frame principal. Kwargs passés à place()."""
        self.frame.place(**kw)

    # ================================================================
    #  Toolbar
    # ================================================================

    def _create_toolbar(self):
        toolbar = tk.Frame(self.frame, bg=self.colors["bg_primary"], bd=0)
        toolbar.place(relx=0.0, rely=0.0, anchor="nw", x=8, y=8)

        btn_style = dict(
            font=("Segoe UI", 11), bd=0, relief="flat", padx=6, pady=2,
            bg=self.colors["bg_primary"], fg=self.colors["text_secondary"],
            activebackground=self.colors["bg_tertiary"],
            activeforeground=self.colors["text_primary"],
            cursor="hand2",
        )

        tk.Button(toolbar, text="⊕ Zoom+", command=self._zoom_in, **btn_style).pack(side="left", padx=2)
        tk.Button(toolbar, text="⊖ Zoom−", command=self._zoom_out, **btn_style).pack(side="left", padx=2)
        tk.Button(toolbar, text="⊙ Reset", command=self._zoom_reset, **btn_style).pack(side="left", padx=2)
        tk.Button(toolbar, text="⊞ Grid", command=self._toggle_grid, **btn_style).pack(side="left", padx=2)

    # ================================================================
    #  Grille de fond
    # ================================================================

    def _draw_grid(self):
        self.canvas.delete("grid")
        if not self._grid_visible:
            return
        w = int(self.canvas.winfo_reqwidth() * 3)
        h = int(self.canvas.winfo_reqheight() * 3)
        step = max(2, int(self.GRID_SIZE * self.zoom))
        dot_r = max(1, int(1.5 * self.zoom))
        color = "#2a2a2a"
        # Convert pan to screen
        ox = self._pan_x % step
        oy = self._pan_y % step
        for x in range(int(ox), w, step):
            for y in range(int(oy), h, step):
                self.canvas.create_oval(
                    x - dot_r, y - dot_r, x + dot_r, y + dot_r,
                    fill=color, outline=color, tags="grid",
                )
        self.canvas.tag_lower("grid")

    def _toggle_grid(self):
        self._grid_visible = not self._grid_visible
        self._redraw()

    # ================================================================
    #  Coord transforms
    # ================================================================

    def _screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        wx = (sx - self._pan_x) / self.zoom
        wy = (sy - self._pan_y) / self.zoom
        return wx, wy

    def _world_to_screen(self, wx: float, wy: float) -> Tuple[float, float]:
        sx = wx * self.zoom + self._pan_x
        sy = wy * self.zoom + self._pan_y
        return sx, sy

    def _snap(self, v: float) -> float:
        if self.snap_to_grid:
            return round(v / self.GRID_SIZE) * self.GRID_SIZE
        return v

    # ================================================================
    #  Nœuds
    # ================================================================

    def add_node(self, agent_type: str, name: str, color: str,
                 wx: Optional[float] = None, wy: Optional[float] = None,
                 icon: str = "🤖") -> int:
        """Ajoute un nœud au canvas. Retourne l'id du nœud."""
        nid = self._next_id
        self._next_id += 1

        if wx is None or wy is None:
            # Placement automatique en cascade
            count = len(self.nodes)
            wx = 80 + (count % 4) * 300
            wy = 60 + (count // 4) * 140

        wx = self._snap(wx)
        wy = self._snap(wy)

        self.nodes[nid] = {
            "agent_type": agent_type,
            "name": name,
            "color": color,
            "icon": icon,
            "x": wx,
            "y": wy,
            "status": "idle",
            "items": [],
        }
        self._draw_node(nid)
        self._refresh_minimap()
        self._fire_changed()
        return nid

    def remove_node(self, nid: int):
        """Supprime un nœud et ses connexions."""
        if nid not in self.nodes:
            return
        # Supprimer les connexions liées
        self.connections = [
            c for c in self.connections
            if c["from"] != nid and c["to"] != nid
        ]
        # Supprimer les items canvas
        for item in self.nodes[nid].get("items", []):
            self.canvas.delete(item)
        del self.nodes[nid]
        self.selected_nodes.discard(nid)
        self._redraw()
        self._fire_changed()

    def set_node_status(self, nid: int, status: str):
        """Change le statut d'un nœud (idle/running/done/error)."""
        if nid in self.nodes and status in self.STATUS_META:
            self.nodes[nid]["status"] = status
            self._redraw()

    def clear(self):
        """Supprime tous les nœuds et connexions."""
        self.canvas.delete("all")  # Supprimer TOUS les items canvas d'abord
        self.nodes.clear()
        self.connections.clear()
        self.selected_nodes.clear()
        self._next_id = 0
        self._redraw()
        self._fire_changed()

    # ── Dessin d'un nœud ───────────────────────────────────────────

    def _draw_node(self, nid: int):
        node = self.nodes[nid]
        for item in node.get("items", []):
            self.canvas.delete(item)

        sx, sy = self._world_to_screen(node["x"], node["y"])
        zoom = self.zoom
        w = self.NODE_W * zoom
        h = self.NODE_H * zoom
        r = 14 * zoom
        color = node["color"]
        status = node["status"]
        selected = nid in self.selected_nodes
        items: list = []
        pad = 16 * zoom

        # ── Ombre ──
        sh = 3 * zoom
        items.append(self._round_rect(
            sx + sh, sy + sh, sx + w + sh, sy + h + sh, r,
            fill="#0a0a12", outline="", tags=f"node_{nid}",
        ))

        # ── Corps (rectangle arrondi) ──
        body_fill = "#252545" if not selected else "#2d2d55"
        border_col = color if selected else "#3a3a5c"
        bw = 2.0 if selected else 1.0
        items.append(self._round_rect(
            sx, sy, sx + w, sy + h, r,
            fill=body_fill, outline=border_col,
            width=bw, tags=f"node_{nid}",
        ))

        # ── Barre colorée (gauche) — rognée aux coins arrondis du rectangle ──
        bar_x = sx
        bar_w = 4 * zoom
        items.append(self.canvas.create_rectangle(
            bar_x - bar_w / 2, sy + r,
            bar_x + bar_w / 2, sy + h - r,
            fill=color, outline="", tags=f"node_{nid}",
        ))

        # ── Icône (cercle coloré + emoji) ──
        icon_text = node.get("icon", "🤖")
        icon_cx = sx + pad + 24 * zoom
        icon_cy = sy + h * 0.5
        icon_r = 18 * zoom
        items.append(self.canvas.create_oval(
            icon_cx - icon_r, icon_cy - icon_r,
            icon_cx + icon_r, icon_cy + icon_r,
            fill=color, outline="", tags=f"node_{nid}",
        ))
        icon_fs = max(12, int(15 * zoom))
        items.append(self.canvas.create_text(
            icon_cx, icon_cy, text=icon_text,
            font=("Segoe UI Emoji", icon_fs), fill="#ffffff",
            tags=f"node_{nid}",
        ))

        # ── Nom ──
        text_x = icon_cx + icon_r + pad
        name_fs = max(9, int(11 * zoom))
        items.append(self.canvas.create_text(
            text_x, sy + h * 0.40,
            text=node["name"], fill="#ffffff",
            font=("Segoe UI", name_fs, "bold"), anchor="w",
            tags=f"node_{nid}",
        ))

        # ── Statut ──
        st = self.STATUS_META[status]
        st_fs = max(7, int(9 * zoom))
        dr = 3.5 * zoom
        dx = text_x + dr
        dy = sy + h * 0.62
        items.append(self.canvas.create_oval(
            dx - dr, dy - dr, dx + dr, dy + dr,
            fill=st["color"], outline="", tags=f"node_{nid}",
        ))
        items.append(self.canvas.create_text(
            dx + 9 * zoom, dy,
            text=st["label"], fill="#9090b0",
            font=("Segoe UI", st_fs), anchor="w",
            tags=f"node_{nid}",
        ))

        # ── Port d'entrée (gauche) ──
        pr = self.PORT_R * zoom
        in_cx, in_cy = sx, sy + h / 2
        items.append(self.canvas.create_oval(
            in_cx - pr, in_cy - pr, in_cx + pr, in_cy + pr,
            fill=body_fill, outline=color, width=1.5,
            tags=(f"node_{nid}", f"port_in_{nid}"),
        ))

        # ── Port de sortie (droite) ──
        out_cx, out_cy = sx + w, sy + h / 2
        items.append(self.canvas.create_oval(
            out_cx - pr, out_cy - pr, out_cx + pr, out_cy + pr,
            fill=body_fill, outline=color, width=1.5,
            tags=(f"node_{nid}", f"port_out_{nid}"),
        ))

        # ── ✕ suppression (dans le rectangle, en haut à droite) ──
        xb_x = sx + w - pad
        xb_y = sy + pad
        items.append(self.canvas.create_text(
            xb_x, xb_y, text="✕",
            fill="#666688",
            font=("Segoe UI", max(8, int(10 * zoom)), "bold"),
            tags=(f"node_{nid}", f"del_{nid}"),
        ))

        node["items"] = items
        for it in items:
            self.canvas.tag_raise(it)

    # ── Rectangle arrondi (polygone) ───────────────────────────────

    def _round_rect(self, x1, y1, x2, y2, r, **kw) -> int:
        points = []
        steps = 8
        for cx, cy, a_start in [
            (x1 + r, y1 + r, 180),
            (x2 - r, y1 + r, 270),
            (x2 - r, y2 - r, 0),
            (x1 + r, y2 - r, 90),
        ]:
            for i in range(steps + 1):
                a = math.radians(a_start + 90 * i / steps)
                points.append(cx + r * math.cos(a))
                points.append(cy - r * math.sin(a))
        return self.canvas.create_polygon(points, smooth=False, **kw)

    # ================================================================
    #  Connexions
    # ================================================================

    def add_connection(self, from_id: int, to_id: int) -> bool:
        """Ajoute une connexion entre deux nœuds. Retourne True si ajoutée."""
        if from_id == to_id:
            return False
        if from_id not in self.nodes or to_id not in self.nodes:
            return False
        # Éviter les doublons
        for c in self.connections:
            if c["from"] == from_id and c["to"] == to_id:
                return False
        # Éviter les cycles simples (A→B et B→A)
        for c in self.connections:
            if c["from"] == to_id and c["to"] == from_id:
                return False
        self.connections.append({"from": from_id, "to": to_id, "line": None})
        self._redraw_connections()
        self._refresh_minimap()
        self._fire_changed()
        return True

    def remove_connection(self, from_id: int, to_id: int):
        """Supprime la connexion entre deux nœuds."""
        self.connections = [
            c for c in self.connections
            if not (c["from"] == from_id and c["to"] == to_id)
        ]
        self._redraw_connections()
        self._refresh_minimap()
        self._fire_changed()

    def _redraw_connections(self):
        self.canvas.delete("conn")
        for conn in self.connections:
            fn = self.nodes.get(conn["from"])
            tn = self.nodes.get(conn["to"])
            if not fn or not tn:
                continue
            # Sortie du nœud source
            sx1, sy1 = self._world_to_screen(
                fn["x"] + self.NODE_W, fn["y"] + self.NODE_H / 2
            )
            # Entrée du nœud cible
            sx2, sy2 = self._world_to_screen(tn["x"], tn["y"] + self.NODE_H / 2)
            pts = self._bezier(sx1, sy1, sx2, sy2)
            line = self.canvas.create_line(
                *pts, fill=fn["color"], width=max(1.5, 2.5 * self.zoom),
                smooth=True, tags="conn",
            )
            # Flèche au bout
            self._draw_arrow_head(sx2, sy2, pts, fn["color"])
            conn["line"] = line
        # Positionner les connexions entre la grille et les nœuds
        if self._grid_visible and self.canvas.find_withtag("grid"):
            self.canvas.tag_lower("conn", "grid")
            self.canvas.tag_raise("conn", "grid")

    def _bezier(self, x1, y1, x2, y2, steps: int = 40) -> list:
        """Courbe de Bézier cubique horizontale."""
        pts = []
        offset = max(50 * self.zoom, abs(x2 - x1) * 0.4)
        cx1, cy1 = x1 + offset, y1
        cx2, cy2 = x2 - offset, y2
        for i in range(steps + 1):
            t = i / steps
            u = 1 - t
            px = u**3 * x1 + 3 * u**2 * t * cx1 + 3 * u * t**2 * cx2 + t**3 * x2
            py = u**3 * y1 + 3 * u**2 * t * cy1 + 3 * u * t**2 * cy2 + t**3 * y2
            pts.extend([px, py])
        return pts

    def _draw_arrow_head(self, tx, ty, pts, color):
        """Dessine une pointe de flèche au point d'arrivée."""
        sz = 8 * self.zoom
        # Direction d'arrivée
        if len(pts) >= 4:
            dx = tx - pts[-4]
            dy = ty - pts[-3]
        else:
            dx, dy = 1, 0
        length = math.hypot(dx, dy) or 1
        dx, dy = dx / length, dy / length
        # Deux points latéraux
        px1 = tx - sz * dx + sz * 0.4 * dy
        py1 = ty - sz * dy - sz * 0.4 * dx
        px2 = tx - sz * dx - sz * 0.4 * dy
        py2 = ty - sz * dy + sz * 0.4 * dx
        self.canvas.create_polygon(
            tx, ty, px1, py1, px2, py2,
            fill=color, outline="", tags="conn",
        )

    # ================================================================
    #  Redraw complet
    # ================================================================

    def _redraw(self):
        self._draw_grid()
        for nid in self.nodes:
            self._draw_node(nid)
        self._redraw_connections()
        self._refresh_minimap()

    # ================================================================
    #  Minimap
    # ================================================================

    def _refresh_minimap(self):
        mm = self._minimap
        mm.delete("all")
        if not self.nodes:
            mm.create_text(
                self.MINIMAP_W / 2, self.MINIMAP_H / 2,
                text="minimap", fill="#555", font=("Segoe UI", 8),
            )
            return

        # Bornes du monde
        xs = [n["x"] for n in self.nodes.values()]
        ys = [n["y"] for n in self.nodes.values()]
        min_x, max_x = min(xs) - 40, max(xs) + self.NODE_W + 40
        min_y, max_y = min(ys) - 40, max(ys) + self.NODE_H + 40
        world_w = max(max_x - min_x, 1)
        world_h = max(max_y - min_y, 1)
        scale = min(self.MINIMAP_W / world_w, self.MINIMAP_H / world_h) * 0.9
        off_x = (self.MINIMAP_W - world_w * scale) / 2
        off_y = (self.MINIMAP_H - world_h * scale) / 2

        def to_mm(wx, wy):
            return (wx - min_x) * scale + off_x, (wy - min_y) * scale + off_y

        # Connexions
        for conn in self.connections:
            fn = self.nodes.get(conn["from"])
            tn = self.nodes.get(conn["to"])
            if fn and tn:
                x1, y1 = to_mm(fn["x"] + self.NODE_W, fn["y"] + self.NODE_H / 2)
                x2, y2 = to_mm(tn["x"], tn["y"] + self.NODE_H / 2)
                mm.create_line(x1, y1, x2, y2, fill="#555", width=1)

        # Nœuds
        for n in self.nodes.values():
            mx, my = to_mm(n["x"], n["y"])
            mw, mh = self.NODE_W * scale, self.NODE_H * scale
            mm.create_rectangle(mx, my, mx + mw, my + mh,
                                fill=n["color"], outline="")

        # Viewport rectangle
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 380
        vx1, vy1 = self._screen_to_world(0, 0)
        vx2, vy2 = self._screen_to_world(cw, ch)
        vsx1, vsy1 = to_mm(vx1, vy1)
        vsx2, vsy2 = to_mm(vx2, vy2)
        mm.create_rectangle(vsx1, vsy1, vsx2, vsy2,
                            outline="#ff6b47", width=1.5, fill="")

    # ================================================================
    #  Zoom
    # ================================================================

    def _zoom_in(self):
        self._apply_zoom(self.zoom * 1.2)

    def _zoom_out(self):
        self._apply_zoom(self.zoom / 1.2)

    def _zoom_reset(self):
        self._pan_x = 0
        self._pan_y = 0
        self._apply_zoom(1.0)

    def _apply_zoom(self, new_zoom: float):
        # Zoom towards center
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 380
        cx, cy = cw / 2, ch / 2
        # World point at center
        wcx = (cx - self._pan_x) / self.zoom
        wcy = (cy - self._pan_y) / self.zoom
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, new_zoom))
        self._pan_x = cx - wcx * self.zoom
        self._pan_y = cy - wcy * self.zoom
        self._redraw()

    def _on_scroll(self, event):
        factor = 1.1 if event.delta > 0 else 1 / 1.1
        # Zoom towards cursor
        mx, my = event.x, event.y
        wcx = (mx - self._pan_x) / self.zoom
        wcy = (my - self._pan_y) / self.zoom
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom * factor))
        self._pan_x = mx - wcx * self.zoom
        self._pan_y = my - wcy * self.zoom
        self._redraw()
        return "break"  # Empêcher la propagation du scroll à la page

    # ================================================================
    #  Événements
    # ================================================================

    def _bind_events(self):
        c = self.canvas
        c.bind("<ButtonPress-1>", self._on_press)
        c.bind("<B1-Motion>", self._on_drag)
        c.bind("<ButtonRelease-1>", self._on_release)
        # Pan: middle or right button
        c.bind("<ButtonPress-2>", self._on_pan_start)
        c.bind("<B2-Motion>", self._on_pan_move)
        c.bind("<ButtonRelease-2>", self._on_pan_end)
        c.bind("<ButtonPress-3>", self._on_right_click)
        c.bind("<B3-Motion>", self._on_pan_move)
        c.bind("<ButtonRelease-3>", self._on_pan_end)
        # Zoom — capture exclusive quand la souris est sur le canvas
        c.bind("<Enter>", self._on_enter_canvas)
        c.bind("<Leave>", self._on_leave_canvas)
        c.bind("<MouseWheel>", self._on_scroll)
        # Delete key
        c.bind("<Delete>", self._on_delete)
        c.bind("<BackSpace>", self._on_delete)
        c.focus_set()

    def _on_enter_canvas(self, _event):
        """Focus le canvas pour capter le MouseWheel (zoom)."""
        self.canvas.focus_set()

    def _on_leave_canvas(self, _event):
        """Rend le focus au parent pour rétablir le scroll de la page."""
        try:
            self.parent.focus_set()
        except Exception:
            pass

    # ── Press ──────────────────────────────────────────────────────

    def _on_press(self, event):
        self.canvas.focus_set()
        sx, sy = event.x, event.y
        wx, wy = self._screen_to_world(sx, sy)

        # 1) Clic sur port de sortie → début connexion
        hit_out = self._hit_output_port(sx, sy)
        if hit_out is not None:
            self._connecting = True
            self._conn_from = hit_out
            node = self.nodes[hit_out]
            start_sx, start_sy = self._world_to_screen(
                node["x"] + self.NODE_W, node["y"] + self.NODE_H / 2
            )
            self._conn_line = self.canvas.create_line(
                start_sx, start_sy, sx, sy,
                fill=node["color"], width=2.5 * self.zoom,
                dash=(6, 3), tags="temp_conn",
            )
            return

        # 2) Clic sur ✕ → supprimer
        del_nid = self._hit_delete_btn(sx, sy)
        if del_nid is not None:
            self.remove_node(del_nid)
            return

        # 3) Clic sur nœud → sélection / début drag
        hit_nid = self._hit_node(sx, sy)
        if hit_nid is not None:
            shift = bool(event.state & 0x1)
            if shift:
                if hit_nid in self.selected_nodes:
                    self.selected_nodes.discard(hit_nid)
                else:
                    self.selected_nodes.add(hit_nid)
            else:
                if hit_nid not in self.selected_nodes:
                    self.selected_nodes = {hit_nid}
            self._drag_node_id = hit_nid
            node = self.nodes[hit_nid]
            self._drag_off = (wx - node["x"], wy - node["y"])
            self._redraw()
            return

        # 4) Clic dans le vide → désélection (ou début sélection rect)
        self.selected_nodes.clear()
        self._sel_start = (sx, sy)
        self._sel_rect = None
        self._redraw()

    # ── Drag ───────────────────────────────────────────────────────

    def _on_drag(self, event):
        sx, sy = event.x, event.y

        # Connexion en cours
        if self._connecting and self._conn_line is not None:
            coords = self.canvas.coords(self._conn_line)
            if len(coords) >= 4:
                self.canvas.coords(self._conn_line, coords[0], coords[1], sx, sy)
            return

        # Drag de nœud
        if self._drag_node_id is not None:
            wx, wy = self._screen_to_world(sx, sy)
            new_x = self._snap(wx - self._drag_off[0])
            new_y = self._snap(wy - self._drag_off[1])
            dx = new_x - self.nodes[self._drag_node_id]["x"]
            dy = new_y - self.nodes[self._drag_node_id]["y"]
            # Déplacer tous les nœuds sélectionnés
            for nid in self.selected_nodes:
                if nid in self.nodes:
                    self.nodes[nid]["x"] += dx
                    self.nodes[nid]["y"] += dy
            if self._drag_node_id not in self.selected_nodes:
                self.nodes[self._drag_node_id]["x"] = new_x
                self.nodes[self._drag_node_id]["y"] = new_y
            self._redraw()
            return

        # Sélection rectangulaire
        if self._sel_start:
            if self._sel_rect:
                self.canvas.delete(self._sel_rect)
            self._sel_rect = self.canvas.create_rectangle(
                self._sel_start[0], self._sel_start[1], sx, sy,
                outline=self.colors["accent"], width=1.5,
                dash=(4, 2), fill="", tags="sel_rect",
            )

    # ── Release ────────────────────────────────────────────────────

    def _on_release(self, event):
        sx, sy = event.x, event.y

        # Fin de connexion
        if self._connecting:
            if self._conn_line:
                self.canvas.delete(self._conn_line)
                self._conn_line = None
            hit_in = self._hit_input_port(sx, sy)
            if hit_in is not None and self._conn_from is not None:
                self.add_connection(self._conn_from, hit_in)
            self._connecting = False
            self._conn_from = None
            return

        # Fin de drag nœud
        if self._drag_node_id is not None:
            self._drag_node_id = None
            self._fire_changed()
            return

        # Fin de sélection rectangulaire
        if self._sel_rect:
            self.canvas.delete(self._sel_rect)
            x1 = min(self._sel_start[0], sx)
            y1 = min(self._sel_start[1], sy)
            x2 = max(self._sel_start[0], sx)
            y2 = max(self._sel_start[1], sy)
            # Sélectionner les nœuds dans le rectangle
            self.selected_nodes.clear()
            for nid, node in self.nodes.items():
                nsx, nsy = self._world_to_screen(node["x"], node["y"])
                nex = nsx + self.NODE_W * self.zoom
                ney = nsy + self.NODE_H * self.zoom
                if nsx < x2 and nex > x1 and nsy < y2 and ney > y1:
                    self.selected_nodes.add(nid)
            self._sel_rect = None
            self._sel_start = (0, 0)
            self._redraw()

    # ── Pan ────────────────────────────────────────────────────────

    def _on_pan_start(self, event):
        self._panning = True
        self._pan_start = (event.x, event.y)

    def _on_right_click(self, event):
        sx, sy = event.x, event.y
        # Check if right-click on a connection (for deletion)
        hit_conn = self._hit_connection(sx, sy)
        if hit_conn is not None:
            conn = self.connections[hit_conn]
            self.remove_connection(conn["from"], conn["to"])
            return
        # Otherwise, start panning
        self._panning = True
        self._pan_start = (event.x, event.y)

    def _on_pan_move(self, event):
        if self._panning:
            dx = event.x - self._pan_start[0]
            dy = event.y - self._pan_start[1]
            self._pan_x += dx
            self._pan_y += dy
            self._pan_start = (event.x, event.y)
            self._redraw()

    def _on_pan_end(self, _event):
        self._panning = False

    # ── Delete ─────────────────────────────────────────────────────

    def _on_delete(self, _event):
        for nid in list(self.selected_nodes):
            self.remove_node(nid)
        self.selected_nodes.clear()

    # ================================================================
    #  Hit testing
    # ================================================================

    def _hit_node(self, sx: float, sy: float) -> Optional[int]:
        """Retourne l'ID du nœud situé sous (sx, sy) ou None."""
        for nid, node in reversed(list(self.nodes.items())):
            nsx, nsy = self._world_to_screen(node["x"], node["y"])
            nw = self.NODE_W * self.zoom
            nh = self.NODE_H * self.zoom
            if nsx <= sx <= nsx + nw and nsy <= sy <= nsy + nh:
                return nid
        return None

    def _hit_output_port(self, sx: float, sy: float) -> Optional[int]:
        pr = self.PORT_R * self.zoom * 2.5  # Zone de clic élargie
        for nid, node in self.nodes.items():
            px, py = self._world_to_screen(
                node["x"] + self.NODE_W, node["y"] + self.NODE_H / 2
            )
            if abs(sx - px) <= pr and abs(sy - py) <= pr:
                return nid
        return None

    def _hit_input_port(self, sx: float, sy: float) -> Optional[int]:
        pr = self.PORT_R * self.zoom * 2.5
        for nid, node in self.nodes.items():
            px, py = self._world_to_screen(node["x"], node["y"] + self.NODE_H / 2)
            if abs(sx - px) <= pr and abs(sy - py) <= pr:
                return nid
        return None

    def _hit_delete_btn(self, sx: float, sy: float) -> Optional[int]:
        r = 12 * self.zoom
        for nid, node in self.nodes.items():
            bx, by = self._world_to_screen(
                node["x"] + self.NODE_W - 10, node["y"] + 12
            )
            if abs(sx - bx) <= r and abs(sy - by) <= r:
                return nid
        return None

    def _hit_connection(self, sx: float, sy: float) -> Optional[int]:
        """Retourne l'index de la connexion la plus proche ou None."""
        threshold = 10 * self.zoom
        for idx, conn in enumerate(self.connections):
            fn = self.nodes.get(conn["from"])
            tn = self.nodes.get(conn["to"])
            if not fn or not tn:
                continue
            x1, y1 = self._world_to_screen(
                fn["x"] + self.NODE_W, fn["y"] + self.NODE_H / 2
            )
            x2, y2 = self._world_to_screen(tn["x"], tn["y"] + self.NODE_H / 2)
            # Approximation: distance au segment
            dist = self._point_to_bezier_distance(sx, sy, x1, y1, x2, y2)
            if dist < threshold:
                return idx
        return None

    def _point_to_bezier_distance(self, px, py, x1, y1, x2, y2) -> float:
        """Distance approx. d'un point à la courbe de Bézier."""
        pts = self._bezier(x1, y1, x2, y2, steps=20)
        min_d = float("inf")
        for i in range(0, len(pts) - 2, 2):
            bx, by = pts[i], pts[i + 1]
            d = math.hypot(px - bx, py - by)
            if d < min_d:
                min_d = d
        return min_d

    # ================================================================
    #  Topologie du workflow (pour l'exécution)
    # ================================================================

    def get_execution_plan(self) -> dict:
        """
        Analyse la topologie des connexions et retourne un plan d'exécution.

        Returns:
            {
                "mode": "empty" | "single" | "sequential" | "parallel" | "dag",
                "steps": [
                    {"nodes": [nid, ...], "parallel": bool},
                    ...
                ],
                "isolated": [nid, ...],   # nœuds sans connexion
                "node_map": {nid: node_data},
            }
        """
        if not self.nodes:
            return {"mode": "empty", "steps": [], "isolated": [], "node_map": {}}

        # Identifier les nœuds connectés / isolés
        connected = set()
        for c in self.connections:
            connected.add(c["from"])
            connected.add(c["to"])
        isolated = [nid for nid in self.nodes if nid not in connected]

        if not self.connections:
            return {
                "mode": "single" if len(self.nodes) == 1 else "parallel",
                "steps": [{"nodes": list(self.nodes.keys()), "parallel": len(self.nodes) > 1}],
                "isolated": isolated,
                "node_map": {nid: dict(n) for nid, n in self.nodes.items()},
            }

        # Tri topologique (Kahn's algorithm)
        in_degree = {nid: 0 for nid in self.nodes}
        adj: Dict[int, List[int]] = {nid: [] for nid in self.nodes}
        for c in self.connections:
            adj[c["from"]].append(c["to"])
            in_degree[c["to"]] = in_degree.get(c["to"], 0) + 1

        queue = [nid for nid in self.nodes if in_degree.get(nid, 0) == 0 and nid in connected]
        steps = []
        visited = set()

        while queue:
            # Tous les nœuds du niveau courant s'exécutent en parallèle
            level = list(queue)
            steps.append({
                "nodes": level,
                "parallel": len(level) > 1,
            })
            visited.update(level)
            next_queue = []
            for nid in level:
                for child in adj.get(nid, []):
                    in_degree[child] -= 1
                    if in_degree[child] == 0 and child not in visited:
                        next_queue.append(child)
            queue = next_queue

        # Déterminer le mode
        is_linear = all(len(s["nodes"]) == 1 for s in steps)
        mode = "sequential" if is_linear else "dag"

        return {
            "mode": mode,
            "steps": steps,
            "isolated": isolated,
            "node_map": {nid: dict(n) for nid, n in self.nodes.items()},
        }

    def get_ordered_agents(self) -> List[Tuple[str, str, str]]:
        """
        Retourne la liste ordonnée (agent_type, name, color) compatible
        avec l'ancien format custom_workflow.
        """
        plan = self.get_execution_plan()
        result = []
        for step in plan["steps"]:
            for nid in step["nodes"]:
                if nid in self.nodes:
                    n = self.nodes[nid]
                    result.append((n["agent_type"], n["name"], n["color"]))
        for nid in plan["isolated"]:
            if nid in self.nodes:
                n = self.nodes[nid]
                result.append((n["agent_type"], n["name"], n["color"]))
        return result

    # ================================================================
    #  Drop depuis l'extérieur
    # ================================================================

    def drop_agent(self, agent_type: str, name: str, color: str,
                   screen_x: int, screen_y: int, icon: str = "🤖") -> int:
        """
        Appelé quand un agent est déposé depuis la grille de cartes.
        screen_x, screen_y sont les coordonnées écran absolues.
        """
        # Convertir en coordonnées canvas
        try:
            cx = screen_x - self.canvas.winfo_rootx()
            cy = screen_y - self.canvas.winfo_rooty()
        except Exception:
            cx, cy = 100, 100
        wx, wy = self._screen_to_world(cx, cy)
        # Centrer le nœud sur le curseur
        wx -= self.NODE_W / 2
        wy -= self.NODE_H / 2
        return self.add_node(agent_type, name, color, wx, wy, icon=icon)

    def is_over(self, screen_x: int, screen_y: int) -> bool:
        """Vérifie si les coordonnées écran sont au-dessus du canvas."""
        try:
            rx = self.canvas.winfo_rootx()
            ry = self.canvas.winfo_rooty()
            rw = self.canvas.winfo_width()
            rh = self.canvas.winfo_height()
            return rx <= screen_x <= rx + rw and ry <= screen_y <= ry + rh
        except Exception:
            return False

    # ================================================================
    #  Callback
    # ================================================================

    def _fire_changed(self):
        if self.on_workflow_changed:
            try:
                self.on_workflow_changed()
            except Exception:
                pass
