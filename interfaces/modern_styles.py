"""
Styles et animations pour l'interface moderne
Contient les définitions CSS-like et animations pour une expérience utilisateur fluide
"""

# Couleurs modernes inspirées de Claude
MODERN_COLORS = {
    # Couleurs principales
    'bg_primary': '#0f0f0f',        # Fond très sombre
    'bg_secondary': '#1a1a1a',      # Fond secondaire
    'bg_tertiary': '#2d2d2d',       # Fond tertiaire
    'bg_chat': '#0f0f0f',           # Zone de conversation
    
    # Bulles de messages
    'bg_user': '#2d5aa0',           # Message utilisateur (bleu)
    'bg_ai': '#1a1a1a',             # Message IA (gris très sombre)
    'bg_ai_thinking': '#1f1f1f',     # IA en réflexion
    
    # Texte
    'text_primary': '#ffffff',       # Texte principal blanc
    'text_secondary': '#9ca3af',     # Texte secondaire gris clair
    'text_muted': '#6b7280',        # Texte atténué
    'text_accent': '#ff6b47',       # Texte d'accent orange
    
    # Interface
    'accent': '#ff6b47',            # Couleur principale (orange Claude)
    'accent_hover': '#ff5730',      # Survol accent
    'accent_light': '#ff8a6b',      # Accent clair
    
    # Bordures et contours
    'border': '#374151',            # Bordures générales
    'border_light': '#4b5563',      # Bordures claires
    'border_focus': '#ff6b47',      # Bordure focus
    
    # États
    'success': '#10b981',           # Vert succès
    'warning': '#f59e0b',           # Orange warning
    'error': '#ef4444',             # Rouge erreur
    'info': '#3b82f6',              # Bleu info
    
    # Zone de saisie
    'input_bg': '#1a1a1a',          # Fond zone de saisie
    'input_border': '#374151',      # Bordure zone de saisie
    'input_focus': '#ff6b47',       # Focus zone de saisie
    'placeholder': '#6b7280',       # Texte placeholder
    
    # Boutons
    'button_primary': '#ff6b47',    # Bouton principal
    'button_secondary': '#374151',  # Bouton secondaire
    'button_hover': '#ff5730',      # Survol bouton
    'button_disabled': '#4b5563',   # Bouton désactivé
    
    # Animations
    'shadow_light': 'rgba(255, 107, 71, 0.1)',
    'shadow_medium': 'rgba(255, 107, 71, 0.2)',
    'shadow_heavy': 'rgba(0, 0, 0, 0.5)',
}

# Animations de pensée
THINKING_ANIMATIONS = [
    "🤖 L'IA réfléchit",
    "🤖 L'IA réfléchit.",
    "🤖 L'IA réfléchit..",
    "🤖 L'IA réfléchit..."
]

# Animations de recherche internet
SEARCH_ANIMATIONS = [
    "🔍 Recherche sur internet",
    "🌐 Recherche sur internet",
    "📡 Recherche sur internet", 
    "🔎 Recherche sur internet",
    "💫 Recherche sur internet",
    "⚡ Recherche sur internet"
]

# Messages de statut
STATUS_MESSAGES = {
    'connected': '● Connecté',
    'thinking': '🧠 Réflexion...',
    'searching': '🔍 Recherche...',
    'processing': '⚙️ Traitement...',
    'error': '❌ Erreur',
    'offline': '● Hors ligne'
}

# Configuration des polices selon l'OS
FONT_CONFIG = {
    'windows': {
        'primary': 'Segoe UI',
        'mono': 'Consolas',
        'emoji': 'Segoe UI Emoji'
    },
    'macos': {
        'primary': 'SF Pro Display',
        'mono': 'SF Mono',
        'emoji': 'Apple Color Emoji'
    },
    'linux': {
        'primary': 'Ubuntu',
        'mono': 'Ubuntu Mono',
        'emoji': 'Noto Color Emoji'
    }
}

# Tailles de police responsive - AUGMENTÉES
FONT_SIZES = {
    'large_screen': {
        'title': 32,
        'subtitle': 18,
        'body': 14,
        'small': 12,
        'chat': 15,         # Plus grande pour les messages
        'code': 13,
        'message': 15,      # Spécial pour les bulles
        'bold': 15          # Pour le texte en gras
    },
    'medium_screen': {
        'title': 28,
        'subtitle': 16,
        'body': 13,
        'small': 11,
        'chat': 14,
        'code': 12,
        'message': 14,
        'bold': 14
    },
    'small_screen': {
        'title': 24,
        'subtitle': 14,
        'body': 12,
        'small': 10,
        'chat': 13,
        'code': 11,
        'message': 13,
        'bold': 13
    }
}

# Configurations d'animation
ANIMATION_CONFIG = {
    'fade_duration': 300,           # Durée des fades en ms
    'slide_duration': 250,          # Durée des slides en ms
    'thinking_interval': 500,       # Intervalle animation pensée
    'search_interval': 800,         # Intervalle animation recherche
    'typing_speed': 50,             # Vitesse d'affichage du texte
    'bounce_height': 5,             # Hauteur du bounce
    'pulse_scale': 1.1              # Échelle du pulse
}

# Layouts responsive
RESPONSIVE_BREAKPOINTS = {
    'small': 800,                   # Écrans petits
    'medium': 1200,                 # Écrans moyens
    'large': 1600                   # Écrans larges
}

RESPONSIVE_LAYOUTS = {
    'small': {
        'sidebar_width': 0,         # Pas de sidebar
        'chat_padding': 10,
        'input_height': 80,
        'message_max_width': '95%'
    },
    'medium': {
        'sidebar_width': 200,
        'chat_padding': 20,
        'input_height': 60,
        'message_max_width': '85%'
    },
    'large': {
        'sidebar_width': 250,
        'chat_padding': 40,
        'input_height': 60,
        'message_max_width': '75%'
    }
}

# Effets visuels
VISUAL_EFFECTS = {
    'message_bounce': {
        'duration': 300,
        'easing': 'ease-out'
    },
    'button_press': {
        'scale': 0.95,
        'duration': 100
    },
    'fade_in': {
        'duration': 400,
        'delay': 100
    },
    'slide_up': {
        'duration': 350,
        'offset': 20
    }
}

# Raccourcis clavier
KEYBOARD_SHORTCUTS = {
    '<Return>': 'send_message',
    '<Shift-Return>': 'new_line',
    '<Control-l>': 'clear_chat',
    '<Control-h>': 'show_help',
    '<Control-o>': 'open_file',
    '<Control-r>': 'refresh',
    '<Escape>': 'cancel_action',
    '<F1>': 'show_help',
    '<F5>': 'refresh'
}

# Messages d'erreur localisés
ERROR_MESSAGES = {
    'file_not_found': "❌ **Fichier introuvable** : Le fichier sélectionné n'existe pas.",
    'file_too_large': "❌ **Fichier trop volumineux** : Veuillez sélectionner un fichier plus petit.",
    'unsupported_format': "❌ **Format non supporté** : Ce type de fichier n'est pas pris en charge.",
    'ai_error': "❌ **Erreur IA** : L'assistant a rencontré un problème. Veuillez réessayer.",
    'network_error': "❌ **Erreur réseau** : Impossible de se connecter pour la recherche internet.",
    'processing_error': "❌ **Erreur de traitement** : Impossible de traiter votre demande.",
    'memory_error': "❌ **Mémoire insuffisante** : Le fichier est trop volumineux pour être traité."
}

# Messages de succès
SUCCESS_MESSAGES = {
    'file_processed': "✅ **Fichier traité** : Le document a été analysé avec succès !",
    'chat_cleared': "✅ **Chat effacé** : Nouvelle conversation démarrée.",
    'ai_ready': "✅ **IA prête** : L'assistant est opérationnel.",
    'search_complete': "✅ **Recherche terminée** : Résultats trouvés et analysés.",
    'export_success': "✅ **Export réussi** : La conversation a été sauvegardée."
}

# Configuration des tooltips
TOOLTIPS = {
    'send_button': "Envoyer le message (Entrée)",
    'clear_button': "Effacer la conversation (Ctrl+L)",
    'help_button': "Afficher l'aide (F1)",
    'file_pdf': "Charger un fichier PDF",
    'file_docx': "Charger un fichier Word",
    'file_code': "Charger un fichier de code",
    'status_indicator': "Statut de connexion à l'IA"
}

# Configuration des notifications
NOTIFICATION_CONFIG = {
    'duration': 3000,              # Durée d'affichage (ms)
    'position': 'top-right',       # Position d'affichage
    'max_notifications': 3,        # Nombre max simultané
    'auto_hide': True,             # Masquage automatique
    'sound': False                 # Son de notification
}
