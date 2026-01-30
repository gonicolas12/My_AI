"""Widget factory mixin for ModernAIGUI."""

import tkinter as tk

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk


class WidgetsMixin:
    """Factory methods for GUI widgets with modern styling."""

    def create_frame(self, parent, **kwargs):
        """Crée un frame avec le bon style"""
        if self.use_ctk:
            # Convertir les paramètres tkinter vers CustomTkinter
            ctk_kwargs = {}
            for key, value in kwargs.items():
                if key == "bg" or key == "fg_color":
                    ctk_kwargs["fg_color"] = value
                elif key == "fg":
                    ctk_kwargs["text_color"] = value
                elif key == "relief":
                    # CustomTkinter ne supporte pas relief, on l'ignore
                    continue
                elif key == "bd" or key == "borderwidth":
                    ctk_kwargs["border_width"] = value
                else:
                    ctk_kwargs[key] = value
            return ctk.CTkFrame(parent, **ctk_kwargs)
        else:
            return tk.Frame(parent, **kwargs)

    def create_label(self, parent, **kwargs):
        """Crée un label avec le bon style"""
        if self.use_ctk:
            # Convertir les paramètres tkinter vers CustomTkinter
            ctk_kwargs = {}
            for key, value in kwargs.items():
                if key == "bg":
                    ctk_kwargs["fg_color"] = value
                elif key == "fg":
                    ctk_kwargs["text_color"] = value
                elif key == "font":
                    ctk_kwargs["font"] = value
                elif key == "text":
                    ctk_kwargs["text"] = value
                elif key in ["relief", "bd", "borderwidth"]:
                    # CustomTkinter ne supporte pas ces paramètres
                    continue
                else:
                    ctk_kwargs[key] = value
            return ctk.CTkLabel(parent, **ctk_kwargs)
        else:
            return tk.Label(parent, **kwargs)

    def create_button(self, parent, text, command, style="primary", **_kwargs):
        """Crée un bouton (alias vers create_modern_button pour compatibilité)"""
        return self.create_modern_button(parent, text, command, style)

    def create_text(self, parent, **kwargs):
        """Crée un widget Text avec le bon style"""
        if self.use_ctk:
            # Convertir les paramètres tkinter vers CustomTkinter
            ctk_kwargs = {}
            for key, value in kwargs.items():
                if key == "bg":
                    ctk_kwargs["fg_color"] = value
                elif key == "fg":
                    ctk_kwargs["text_color"] = value
                elif key == "font":
                    ctk_kwargs["font"] = value
                elif key == "wrap":
                    ctk_kwargs["wrap"] = value
                elif key in ["relief", "bd", "borderwidth"]:
                    # CustomTkinter ne supporte pas ces paramètres
                    continue
                else:
                    ctk_kwargs[key] = value
            return ctk.CTkTextbox(parent, **ctk_kwargs)
        else:
            return tk.Text(parent, **kwargs)

    def create_modern_button(self, parent, text, command, style="primary"):
        """Crée un bouton moderne avec différents styles"""
        # Initialisation des valeurs par défaut
        bg_color = self.colors["accent"]
        hover_color = "#ff5730"
        text_color = "#ffffff"

        if style == "primary":
            bg_color = self.colors["accent"]
            hover_color = "#ff5730"
            text_color = "#ffffff"
        elif style == "secondary":
            bg_color = self.colors["bg_secondary"]
            hover_color = self.colors["button_hover"]
            text_color = self.colors["text_primary"]
        elif style == "file":
            bg_color = self.colors["bg_secondary"]
            hover_color = self.colors["button_hover"]
            text_color = self.colors["text_secondary"]

        if self.use_ctk:
            return ctk.CTkButton(
                parent,
                text=text,
                command=command,
                fg_color=bg_color,
                hover_color=hover_color,
                text_color=text_color,
                font=(
                    "Segoe UI",
                    self.get_current_font_size("message"),
                ),  # UNIFIÉ AVEC LES MESSAGES
                corner_radius=6,
                height=32,
            )
        else:
            btn = tk.Button(
                parent,
                text=text,
                command=command,
                bg=bg_color,
                fg=text_color,
                font=(
                    "Segoe UI",
                    self.get_current_font_size("message"),
                ),  # UNIFIÉ AVEC LES MESSAGES
                border=0,
                relief="flat",
            )

            # Effet hover pour tkinter standard
            def on_enter(_e):
                btn.configure(bg=hover_color)

            def on_leave(_e):
                btn.configure(bg=bg_color)

            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

            return btn
