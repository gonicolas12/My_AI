"""Settings panel mixin — fenêtre ⚙️ Réglages (modèles, paramètres, toggles).

Fenêtre Toplevel autonome qui remplace l'édition manuelle de config.yaml /
Modelfile / .bat. Elle RÉUTILISE les helpers de interfaces/onboarding.py
(ollama_reachable, list_installed_models, pull_model, apply_model_choice,
create_custom_model, apply_generation_params, set_config_flag, marker_path)
et persiste en PRÉSERVANT les commentaires de config.yaml.

100% local : pull/création du modèle tournent en thread, callbacks via
self.root.after(). Conteneur = tk.Toplevel (pattern éprouvé de _show_relay_info_popup,
évite le bug CTkToplevel) peuplé de widgets CTk quand disponibles, sinon tk.

Sections :
  1. Modèles Ollama : lister, choisir le modèle de base, pull (barre de
     progression), Appliquer = apply_model_choice + create_custom_model
     (régénère proprement 'my_ai', system prompt préservé → résout 7.4.0).
  2. Paramètres généraux : température, num_ctx, timeout (config + Modelfile,
     + mise à jour live de l'instance LocalLLM en cours).
  3. Autres réglages : langue par défaut, lecture vocale auto (tts_autoread),
     relay.auto_start, et relance de l'assistant d'onboarding.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk

from core.config import get_config
from interfaces import onboarding


_WIN_W, _WIN_H = 660, 780


class SettingsPanelMixin:
    """Fenêtre ⚙️ Réglages pour ModernAIGUI."""

    # ─── Ouverture ──────────────────────────────────────────────────────

    def open_settings_window(self):
        """Ouvre (ou refocus) la fenêtre Réglages."""
        existing = getattr(self, "_settings_win", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return
            except Exception:
                pass

        bg = self.colors.get("bg_primary", "#212121")
        win = tk.Toplevel(self.root)
        win.title("⚙️ Réglages — My_AI")
        win.configure(bg=bg)
        win.geometry(f"{_WIN_W}x{_WIN_H}")
        win.transient(self.root)
        win.resizable(False, True)
        self._settings_win = win

        def _on_close():
            self._settings_win = None
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", _on_close)

        # Conteneur scrollable
        if CTK_AVAILABLE:
            scroll = ctk.CTkScrollableFrame(win, fg_color=bg, corner_radius=0)
        else:
            scroll = tk.Frame(win, bg=bg)
        scroll.pack(fill="both", expand=True, padx=4, pady=4)
        self._settings_scroll = scroll

        self._build_models_section(scroll)
        self._build_params_section(scroll)
        self._build_toggles_section(scroll)

        # Charger l'état Ollama + modèles installés en arrière-plan
        self._settings_refresh_models()

    # ─── Helpers de style ───────────────────────────────────────────────

    def _st_frame(self, parent, color=None):
        bg = color or self.colors.get("bg_primary", "#212121")
        if CTK_AVAILABLE:
            return ctk.CTkFrame(parent, fg_color=bg, corner_radius=0)
        return tk.Frame(parent, bg=bg)

    def _st_label(self, parent, text, size=12, bold=False, color=None):
        c = color or self.colors.get("text_primary", "#ffffff")
        font = ("Segoe UI", size, "bold" if bold else "normal")
        if CTK_AVAILABLE:
            return ctk.CTkLabel(parent, text=text, font=font, text_color=c,
                                fg_color="transparent")
        bg = self.colors.get("bg_primary", "#212121")
        return tk.Label(parent, text=text, font=font, fg=c, bg=bg)

    def _st_separator(self, parent):
        bg = self.colors.get("border", "#404040")
        if CTK_AVAILABLE:
            f = ctk.CTkFrame(parent, height=1, fg_color=bg, corner_radius=0)
        else:
            f = tk.Frame(parent, height=1, bg=bg)
        f.pack(fill="x", padx=10, pady=(2, 6))

    def _st_button(self, parent, text, command, accent=False, color=None):
        if color:
            bg = color
        elif accent:
            bg = self.colors.get("accent", "#ff6b47")
        else:
            bg = self.colors.get("bg_secondary", "#2f2f2f")
        hover = (self.colors.get("accent_hover", "#e85a3a") if accent
                 else self.colors.get("button_hover", "#404040"))
        tc = self.colors.get("text_primary", "#ffffff")
        if CTK_AVAILABLE:
            return ctk.CTkButton(parent, text=text, command=command,
                                 fg_color=bg, hover_color=hover, text_color=tc,
                                 font=("Segoe UI", 12), height=32, corner_radius=6)
        return tk.Button(parent, text=text, command=command, bg=bg, fg=tc,
                         font=("Segoe UI", 12), relief="flat")

    def _st_section_title(self, parent, text):
        accent = self.colors.get("accent", "#ff6b47")
        f = self._st_frame(parent)
        f.pack(fill="x", padx=10, pady=(14, 2))
        self._st_label(f, text, size=15, bold=True, color=accent).pack(anchor="w")
        self._st_separator(parent)

    def _st_make_switch(self, parent, text, variable, command):
        row = self._st_frame(parent)
        row.pack(fill="x", pady=4)
        if CTK_AVAILABLE:
            sw = ctk.CTkSwitch(row, text=text, variable=variable, command=command,
                               font=("Segoe UI", 12),
                               progress_color=self.colors.get("accent", "#ff6b47"),
                               text_color=self.colors.get("text_primary", "#ffffff"))
        else:
            sw = tk.Checkbutton(row, text=text, variable=variable, command=command,
                                bg=self.colors.get("bg_primary", "#212121"),
                                fg=self.colors.get("text_primary", "#ffffff"),
                                selectcolor=self.colors.get("bg_primary", "#212121"),
                                font=("Segoe UI", 12), anchor="w")
        sw.pack(anchor="w")
        return sw

    # ─── Section 1 : Modèles Ollama ─────────────────────────────────────

    def _build_models_section(self, parent):
        self._st_section_title(parent, "🧠 Modèles Ollama")
        body = self._st_frame(parent)
        body.pack(fill="x", padx=10, pady=(0, 4))

        self._st_ollama_status = self._st_label(
            body, "Vérification d'Ollama…", size=11,
            color=self.colors.get("text_secondary", "#9ca3af"))
        self._st_ollama_status.pack(anchor="w", pady=(0, 6))

        # Modèle de base
        row = self._st_frame(body)
        row.pack(fill="x", pady=2)
        self._st_label(row, "Modèle de base :", size=12).pack(side="left", padx=(0, 8))
        self._st_model_var = tk.StringVar(value=onboarding.current_base_model())
        if CTK_AVAILABLE:
            self._st_model_menu = ctk.CTkOptionMenu(
                row, values=[self._st_model_var.get()], variable=self._st_model_var,
                fg_color=self.colors.get("bg_secondary", "#2f2f2f"),
                button_color=self.colors.get("accent", "#ff6b47"),
                button_hover_color=self.colors.get("accent_hover", "#e85a3a"),
                width=220)
        else:
            self._st_model_menu = tk.OptionMenu(row, self._st_model_var,
                                                self._st_model_var.get())
        self._st_model_menu.pack(side="left")

        self._st_installed_lbl = self._st_label(
            body, "Modèles installés : …", size=10,
            color=self.colors.get("text_secondary", "#9ca3af"))
        self._st_installed_lbl.pack(anchor="w", pady=(6, 4))

        # Pull d'un nouveau modèle
        prow = self._st_frame(body)
        prow.pack(fill="x", pady=2)
        self._st_label(prow, "Télécharger :", size=12).pack(side="left", padx=(0, 8))
        self._st_pull_var = tk.StringVar()
        if CTK_AVAILABLE:
            pull_entry = ctk.CTkEntry(
                prow, textvariable=self._st_pull_var,
                placeholder_text="ex : qwen3.5:4b", width=180,
                fg_color=self.colors.get("bg_secondary", "#2f2f2f"))
        else:
            pull_entry = tk.Entry(prow, textvariable=self._st_pull_var)
        pull_entry.pack(side="left", padx=(0, 6))
        self._st_pull_btn = self._st_button(prow, "⬇ Pull", self._settings_pull_model)
        self._st_pull_btn.pack(side="left")

        # Barre de progression
        if CTK_AVAILABLE:
            self._st_progress = ctk.CTkProgressBar(
                body, progress_color=self.colors.get("accent", "#ff6b47"))
            self._st_progress.set(0)
            self._st_progress.pack(fill="x", pady=(8, 2))
        else:
            self._st_progress = None
        self._st_progress_lbl = self._st_label(
            body, "", size=10, color=self.colors.get("text_secondary", "#9ca3af"))
        self._st_progress_lbl.pack(anchor="w")

        # Zone de log
        if CTK_AVAILABLE:
            self._st_log = ctk.CTkTextbox(body, height=110, font=("Consolas", 10))
        else:
            self._st_log = tk.Text(body, height=6, font=("Consolas", 10))
        self._st_log.pack(fill="x", pady=(4, 6))
        try:
            self._st_log.configure(state="disabled")
        except Exception:
            pass

        # Appliquer (régénère my_ai)
        self._st_apply_btn = self._st_button(
            body, "✅ Appliquer (régénère le modèle 'my_ai')",
            self._settings_apply_model, accent=True)
        self._st_apply_btn.pack(fill="x", pady=(2, 4))
        self._st_label(
            body, "Régénère proprement le modèle personnalisé (system prompt préservé).",
            size=9, color=self.colors.get("text_secondary", "#9ca3af")).pack(anchor="w")

    def _settings_log(self, msg):
        def _append():
            try:
                self._st_log.configure(state="normal")
                self._st_log.insert("end", str(msg).rstrip() + "\n")
                self._st_log.see("end")
                self._st_log.configure(state="disabled")
            except Exception:
                pass
        try:
            self.root.after(0, _append)
        except Exception:
            pass

    def _settings_set_progress(self, frac, status):
        def _upd():
            try:
                if self._st_progress is not None:
                    self._st_progress.set(max(0.0, min(1.0, frac)))
                self._st_progress_lbl.configure(text=f"{status} — {int(frac * 100)}%")
            except Exception:
                pass
        try:
            self.root.after(0, _upd)
        except Exception:
            pass

    def _settings_refresh_models(self):
        def _work():
            reachable = onboarding.ollama_reachable()
            models = onboarding.list_installed_models() if reachable else []

            def _apply():
                if not reachable:
                    self._st_ollama_status.configure(
                        text="⚠️ Ollama non détecté — démarrez-le pour gérer les modèles",
                        text_color=self.colors.get("warning", "#f59e0b"))
                else:
                    self._st_ollama_status.configure(
                        text="✅ Ollama actif", text_color="#10b981")
                if models:
                    self._st_installed_lbl.configure(
                        text="Modèles installés : " + ", ".join(models))
                    self._settings_update_model_menu(models)
                else:
                    self._st_installed_lbl.configure(text="Modèles installés : (aucun)")
            try:
                self.root.after(0, _apply)
            except Exception:
                pass
        threading.Thread(target=_work, daemon=True).start()

    def _settings_update_model_menu(self, models):
        # On choisit un modèle de BASE → exclure le custom 'my_ai' de la liste.
        bases = [m for m in models if not m.startswith("my_ai")] or list(models)
        cur = self._st_model_var.get()
        if cur and cur not in bases:
            bases = [cur] + bases
        try:
            if CTK_AVAILABLE:
                self._st_model_menu.configure(values=bases)
            else:
                menu = self._st_model_menu["menu"]
                menu.delete(0, "end")
                for m in bases:
                    menu.add_command(label=m,
                                     command=lambda v=m: self._st_model_var.set(v))
        except Exception:
            pass

    def _st_set_busy(self, busy):
        state = "disabled" if busy else "normal"
        for attr in ("_st_pull_btn", "_st_apply_btn"):
            btn = getattr(self, attr, None)
            if btn is not None:
                try:
                    btn.configure(state=state)
                except Exception:
                    pass

    def _settings_pull_model(self):
        name = (self._st_pull_var.get() or "").strip()
        if not name:
            messagebox.showinfo("Pull", "Entrez un nom de modèle (ex : qwen3.5:4b).",
                                parent=self._settings_win)
            return
        if not onboarding.ollama_reachable():
            messagebox.showwarning("Ollama", "Ollama n'est pas joignable.",
                                   parent=self._settings_win)
            return
        self._st_set_busy(True)
        self._settings_log(f"📥 Téléchargement de {name}…")

        def _work():
            ok = True
            try:
                onboarding.pull_model(name, self._settings_set_progress, self._settings_log)
                self._settings_log(f"✅ {name} téléchargé.")
            except Exception as exc:
                ok = False
                self._settings_log(f"❌ Erreur pull : {exc}")

            def _done():
                self._st_set_busy(False)
                if ok:
                    self.show_notification(f"✅ {name} téléchargé", "success", 2500)
                    self._settings_refresh_models()
                else:
                    self.show_notification("❌ Échec du téléchargement", "error", 3000)
            try:
                self.root.after(0, _done)
            except Exception:
                pass
        threading.Thread(target=_work, daemon=True).start()

    def _settings_apply_model(self):
        base = (self._st_model_var.get() or "").strip()
        if not base:
            return
        if not onboarding.ollama_reachable():
            messagebox.showwarning("Ollama", "Ollama n'est pas joignable.",
                                   parent=self._settings_win)
            return
        if not messagebox.askyesno(
                "Appliquer",
                f"Régénérer le modèle 'my_ai' à partir de « {base} » ?\n"
                "Le system prompt du Modelfile sera préservé.",
                parent=self._settings_win):
            return
        self._st_set_busy(True)
        self._settings_log(f"🔧 Modelfile FROM → {base}")

        def _work():
            ok = True
            try:
                onboarding.apply_model_choice(base)
                self._settings_log("🏗️  Création du modèle 'my_ai'…")
                onboarding.create_custom_model(self._settings_log)
                self._settings_log("✅ Modèle 'my_ai' régénéré.")
            except Exception as exc:
                ok = False
                self._settings_log(f"❌ Erreur : {exc}")

            def _done():
                self._st_set_busy(False)
                if ok:
                    self.show_notification("✅ Modèle 'my_ai' régénéré", "success", 3000)
                    self._settings_refresh_models()
                else:
                    self.show_notification("❌ Échec de la régénération", "error", 3000)
            try:
                self.root.after(0, _done)
            except Exception:
                pass
        threading.Thread(target=_work, daemon=True).start()

    # ─── Section 2 : Paramètres généraux ────────────────────────────────

    def _build_params_section(self, parent):
        self._st_section_title(parent, "⚙️ Paramètres généraux")
        body = self._st_frame(parent)
        body.pack(fill="x", padx=10, pady=(0, 4))
        cfg = get_config()

        # Température (slider 0.0–1.0)
        trow = self._st_frame(body)
        trow.pack(fill="x", pady=4)
        self._st_temp_var = tk.DoubleVar(value=float(cfg.get("llm.local.temperature", 0.7)))
        self._st_label(trow, "Température :", size=12).pack(side="left", padx=(0, 8))
        self._st_temp_lbl = self._st_label(trow, "", size=12)
        self._st_temp_lbl.pack(side="right", padx=(8, 0))

        def _temp_changed(v):
            try:
                self._st_temp_lbl.configure(text=f"{float(v):.2f}")
            except Exception:
                pass

        if CTK_AVAILABLE:
            slider = ctk.CTkSlider(
                trow, from_=0.0, to=1.0, number_of_steps=20,
                variable=self._st_temp_var, command=_temp_changed,
                progress_color=self.colors.get("accent", "#ff6b47"),
                button_color=self.colors.get("accent", "#ff6b47"))
        else:
            slider = tk.Scale(trow, from_=0.0, to=1.0, resolution=0.05,
                              orient="horizontal", variable=self._st_temp_var,
                              command=_temp_changed, showvalue=False)
        slider.pack(side="left", fill="x", expand=True)
        _temp_changed(self._st_temp_var.get())

        # num_ctx (option menu)
        crow = self._st_frame(body)
        crow.pack(fill="x", pady=4)
        self._st_label(crow, "Fenêtre de contexte (num_ctx) :", size=12).pack(
            side="left", padx=(0, 8))
        self._st_ctx_var = tk.StringVar(value=str(cfg.get("llm.local.num_ctx", 16384)))
        ctx_values = ["2048", "4096", "8192", "16384", "32768"]
        if self._st_ctx_var.get() not in ctx_values:
            ctx_values.append(self._st_ctx_var.get())
        if CTK_AVAILABLE:
            ctx_menu = ctk.CTkOptionMenu(
                crow, values=ctx_values, variable=self._st_ctx_var,
                fg_color=self.colors.get("bg_secondary", "#2f2f2f"),
                button_color=self.colors.get("accent", "#ff6b47"),
                button_hover_color=self.colors.get("accent_hover", "#e85a3a"),
                width=120)
        else:
            ctx_menu = tk.OptionMenu(crow, self._st_ctx_var, *ctx_values)
        ctx_menu.pack(side="left")

        # timeout (entry, secondes)
        torow = self._st_frame(body)
        torow.pack(fill="x", pady=4)
        self._st_label(torow, "Timeout requête LLM (s) :", size=12).pack(
            side="left", padx=(0, 8))
        self._st_timeout_var = tk.StringVar(value=str(cfg.get("llm.local.timeout", 1200)))
        if CTK_AVAILABLE:
            to_entry = ctk.CTkEntry(
                torow, textvariable=self._st_timeout_var, width=100,
                fg_color=self.colors.get("bg_secondary", "#2f2f2f"))
        else:
            to_entry = tk.Entry(torow, textvariable=self._st_timeout_var, width=8)
        to_entry.pack(side="left")

        self._st_button(body, "💾 Enregistrer les paramètres",
                        self._settings_save_params, accent=True).pack(fill="x", pady=(8, 4))
        self._st_label(
            body, "Écrit dans config.yaml + Modelfile (commentaires préservés) "
            "et applique immédiatement.", size=9,
            color=self.colors.get("text_secondary", "#9ca3af")).pack(anchor="w")

    def _settings_save_params(self):
        try:
            temperature = round(float(self._st_temp_var.get()), 2)
        except Exception:
            temperature = 0.7
        try:
            num_ctx = int(self._st_ctx_var.get())
        except Exception:
            num_ctx = 16384
        try:
            timeout = int(float(self._st_timeout_var.get()))
        except Exception:
            timeout = 1200
        timeout = max(30, min(7200, timeout))

        try:
            onboarding.apply_generation_params(
                temperature=temperature, num_ctx=num_ctx, timeout=timeout)
        except Exception as exc:
            self.show_notification(f"❌ Erreur : {exc}", "error", 3000)
            return

        # Application live sur l'instance LocalLLM en cours (sans redémarrage)
        try:
            llm = getattr(getattr(getattr(self, "ai_engine", None),
                                  "local_ai", None), "local_llm", None)
            if llm is not None:
                llm.gen_temperature = temperature
                llm.gen_num_ctx = num_ctx
                llm.timeout = timeout
        except Exception:
            pass
        self.show_notification("💾 Paramètres enregistrés", "success", 2500)

    # ─── Section 3 : Autres réglages ────────────────────────────────────

    def _build_toggles_section(self, parent):
        self._st_section_title(parent, "🎚️ Autres réglages")
        body = self._st_frame(parent)
        body.pack(fill="x", padx=10, pady=(0, 4))
        cfg = get_config()

        # Langue par défaut
        lrow = self._st_frame(body)
        lrow.pack(fill="x", pady=4)
        self._st_label(lrow, "Langue par défaut :", size=12).pack(side="left", padx=(0, 8))
        supported = cfg.get("language.supported", ["fr", "en"]) or ["fr", "en"]
        self._st_lang_var = tk.StringVar(value=str(cfg.get("language.default", "fr")))
        if CTK_AVAILABLE:
            lang_menu = ctk.CTkOptionMenu(
                lrow, values=[str(s) for s in supported], variable=self._st_lang_var,
                command=lambda v: self._settings_set_flag("language.default", v,
                                                          notify="Langue"),
                fg_color=self.colors.get("bg_secondary", "#2f2f2f"),
                button_color=self.colors.get("accent", "#ff6b47"),
                button_hover_color=self.colors.get("accent_hover", "#e85a3a"),
                width=100)
        else:
            lang_menu = tk.OptionMenu(
                lrow, self._st_lang_var, *[str(s) for s in supported],
                command=lambda v: self._settings_set_flag("language.default", v,
                                                          notify="Langue"))
        lang_menu.pack(side="left")

        # Lecture vocale auto
        self._st_tts_var = tk.BooleanVar(
            value=bool(getattr(self, "tts_autoread", cfg.get("ui.tts_autoread", False))))
        self._st_make_switch(body, "🔊 Lecture vocale automatique des réponses",
                             self._st_tts_var, self._settings_toggle_tts)

        # Relay auto-start
        self._st_relay_var = tk.BooleanVar(value=bool(cfg.get("relay.auto_start", False)))
        self._st_make_switch(
            body, "📡 Démarrer le Relay au lancement", self._st_relay_var,
            lambda: self._settings_set_flag(
                "relay.auto_start", bool(self._st_relay_var.get()),
                notify="Relay auto-start"))
        self._st_label(
            body, "(Le Relay auto-start prend effet au prochain démarrage.)", size=9,
            color=self.colors.get("text_secondary", "#9ca3af")).pack(anchor="w", pady=(0, 4))

        self._st_separator(body)

        # Relancer l'onboarding
        self._st_button(body, "🔄 Relancer l'assistant de configuration",
                        self._settings_reset_onboarding).pack(fill="x", pady=(4, 4))
        self._st_label(
            body, "Supprime le marqueur ; l'assistant s'affichera au prochain démarrage.",
            size=9, color=self.colors.get("text_secondary", "#9ca3af")).pack(anchor="w")

    def _settings_toggle_tts(self):
        val = bool(self._st_tts_var.get())
        self.tts_autoread = val
        # Synchroniser le bouton TTS de la sidebar s'il existe
        btn = getattr(self, "_sidebar_tts_btn", None)
        if btn is not None:
            try:
                accent = self.colors.get("accent", "#ff6b47")
                inactive = self.colors.get("bg_tertiary", "#3a3a3a")
                label = "🔊 Lecture auto : ON" if val else "🔇 Lecture auto : OFF"
                if CTK_AVAILABLE:
                    btn.configure(text=label, fg_color=accent if val else inactive)
                else:
                    btn.configure(text=label, bg=accent if val else inactive)
            except Exception:
                pass
        self._settings_set_flag("ui.tts_autoread", val, notify="Lecture vocale")

    def _settings_set_flag(self, name, value, notify=None):
        try:
            onboarding.set_config_flag(name, value)
            if notify:
                self.show_notification(f"💾 {notify} enregistré", "success", 1800)
        except Exception as exc:
            self.show_notification(f"❌ Erreur : {exc}", "error", 2500)

    def _settings_reset_onboarding(self):
        if not messagebox.askyesno(
                "Relancer l'assistant",
                "Relancer l'assistant de configuration au prochain démarrage ?",
                parent=self._settings_win):
            return
        try:
            marker = onboarding.marker_path()
            if marker.exists():
                marker.unlink()
            self.show_notification(
                "🔄 L'assistant s'affichera au prochain démarrage", "success", 3000)
        except Exception as exc:
            self.show_notification(f"❌ Erreur : {exc}", "error", 2500)
