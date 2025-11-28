"""
Module de gestion des LLM locaux avec priorité à Ollama.
"""
import requests

class LocalLLM:
    """
    Gestionnaire intelligent de LLM Local.
    Tente d'utiliser Ollama en priorité, sinon gère le fallback.
    """
    def __init__(self, model="my_ai", ollama_url="http://localhost:11434/api/generate", timeout=180):
        # On essaie d'abord le modèle personnalisé 'my_ai', sinon fallback sur 'llama3'
        self.model = model
        self.ollama_url = ollama_url
        self.timeout = timeout  # Timeout configurable (180s par défaut)
        self.is_ollama_available = self._check_ollama_availability()

        if self.is_ollama_available:
            # Vérifier si le modèle personnalisé existe, sinon utiliser llama3
            if not self._check_model_exists(model):
                print(f"⚠️ [LocalLLM] Modèle '{model}' non trouvé. Fallback sur 'llama3'.")
                self.model = "llama3"

            print(f"✅ [LocalLLM] Ollama détecté et actif sur {self.ollama_url} (Modèle: {self.model})")
            print(f"   ℹ️  Timeout configuré: {self.timeout}s (la première requête peut être lente)")
        else:
            print("⚠️ [LocalLLM] Ollama non détecté. Le mode génératif avancé sera désactivé.")

    def _check_model_exists(self, model_name):
        """Vérifie si le modèle existe dans Ollama"""
        try:
            response = requests.get(self.ollama_url.replace("/api/generate", "/api/tags"), timeout=2)
            if response.status_code == 200:
                models = [m['name'] for m in response.json().get('models', [])]
                # Vérifie si le modèle est dans la liste (avec ou sans tag :latest)
                return any(model_name in m for m in models)
            return False
        except Exception:
            return False

    def _check_ollama_availability(self):
        """Vérifie si le serveur Ollama répond"""
        try:
            # On tente juste un ping rapide (GET sur la racine ou une API légère)
            response = requests.get(self.ollama_url.replace("/api/generate", ""), timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def generate(self, prompt, system_prompt=None):
        """
        Génère une réponse.
        Retourne None si Ollama n'est pas disponible (pour déclencher le fallback).
        """
        if not self.is_ollama_available:
            return None

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\nUser: {prompt}"

        data = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 4096,  # Contexte équilibré performance/vitesse
                "num_predict": 1024  # Réponses plus complètes
            }
        }

        try:
            print(f"⏳ [LocalLLM] Génération en cours (timeout: {self.timeout}s)...")
            response = requests.post(self.ollama_url, json=data, timeout=self.timeout)
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                print(f"⚠️ [LocalLLM] Erreur API Ollama: {response.status_code}")
                return None
        except requests.exceptions.Timeout:
            print(f"⚠️ [LocalLLM] Timeout après {self.timeout}s - Le modèle est trop lent.")
            print("   💡 Conseil: Essayez un modèle plus léger (llama3.2) ou augmentez le timeout.")
            return None
        except Exception as e:
            print(f"⚠️ [LocalLLM] Exception durant la génération: {e}")
            return None
