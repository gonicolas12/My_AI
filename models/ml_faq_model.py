"""
Modèle à base de Questions / Réponses
"""
import glob
import json
import os
import re
import unicodedata

from rapidfuzz import fuzz

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError as e:
    raise ImportError("scikit-learn n'est pas installé. Installez-le avec 'pip install scikit-learn'.") from e

class MLFAQModel:
    """Modèle ML FAQ"""
    def _fit_vectorizer(self):
        self.vectorizer = TfidfVectorizer()
        self.question_vecs = self.vectorizer.fit_transform(self.questions)
    def _load_examples(self):
        self.questions = []
        self.answers = []
        # Charger d'abord la base culture générale (prioritaire)
        culture_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/enrichissement/enrichissement_culture.jsonl'))
        if os.path.exists(culture_path):
            with open(culture_path, encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                        norm_q = self.normalize(obj['input'])
                        self.questions.append(norm_q)
                        self.answers.append(obj['target'])
                    except Exception :
                        continue
        # Charger ensuite les autres fichiers (sauf culture déjà chargé)
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/enrichissement'))
        files = glob.glob(os.path.join(data_dir, 'enrichissement*.jsonl'))
        for file in files:
            if os.path.abspath(file) == culture_path:
                continue  # déjà chargé
            with open(file, encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                        norm_q = self.normalize(obj['input'])
                        self.questions.append(norm_q)
                        self.answers.append(obj['target'])
                    except Exception:
                        continue

    def __init__(self, data_path=None, debug=True):
        # Toujours initialiser self.debug pour éviter les erreurs d'attribut
        self.debug = debug
        if data_path is None:
            data_path = os.path.join(os.path.dirname(__file__), '../data/enrichissement_exemples.jsonl')
        self.data_path = os.path.abspath(data_path)
        self.questions = []
        self.answers = []
        self.vectorizer = TfidfVectorizer()
        self.question_vecs = None
        self._loaded = False  # Lazy loading: données chargées au premier predict()

    @staticmethod
    def normalize(text):
        """Normalisation"""
        # Minuscule, suppression accents, apostrophes, ponctuation, espaces multiples, caractères non-alphanumériques
        text = text.lower()
        text = text.replace("'", " ")  # remplace apostrophes par espace
        text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
        # Remplace toute ponctuation/séparateur par un espace
        text = ''.join(c if c.isalnum() else ' ' for c in text)
        text = re.sub(r'\s+', ' ', text)  # Un seul espace entre chaque mot
        text = text.strip()
        return text

    def _ensure_loaded(self):
        """Charge les données si pas encore fait (lazy loading)"""
        if not self._loaded:
            self._load_examples()
            self._fit_vectorizer()
            self._loaded = True

    def predict(self, question, threshold=0.5):
        """
        Retourne la réponse la plus proche si la similarité est suffisante, sinon None.
        Ajoute un bypass exact-match et un fallback fuzzy (rapidfuzz).
        Ajoute des logs détaillés pour la normalisation.
        """
        self._ensure_loaded()
        threshold = 0.9  # Plus strict pour éviter les faux positifs
        seuil_fuzzy = 92
        norm_q = self.normalize(question)
        # Debug minimal : affiche uniquement la question et la question normalisée
        # print(f"[MLFAQModel] predict: question={repr(question)} | norm_q={repr(norm_q)}")

        # 1. Bypass exact-match (ultra robuste)
        for idx, q in enumerate(self.questions):
            if norm_q == q:
                print(f"[MLFAQModel] Match exact trouvé pour: {repr(norm_q)} (index {idx})")
                print(f"[MLFAQModel] Réponse: {self.answers[idx]}")
                return self.answers[idx]
        # Debug supplémentaire si pas de match exact
        # print(f"[MLFAQModel] Pas de match exact pour: {repr(norm_q)} (input normalisé)")

        # 2. TF-IDF similarity
        vec = self.vectorizer.transform([norm_q])
        sims = cosine_similarity(vec, self.question_vecs)[0]
        best_idx = sims.argmax()
        if sims[best_idx] >= threshold:
            print(f"[MLFAQModel] Match TF-IDF trouvé pour: '{norm_q}' (score={sims[best_idx]:.2f})")
            return self.answers[best_idx]

        # 3. Fallback fuzzy matching (rapidfuzz)
        try:
            fuzzy_scores = [fuzz.ratio(norm_q, q) for q in self.questions]
            best_fuzzy_idx = int(max(range(len(fuzzy_scores)), key=lambda i: fuzzy_scores[i]))
            best_fuzzy_score = fuzzy_scores[best_fuzzy_idx]
            if best_fuzzy_score >= seuil_fuzzy:
                print(f"[MLFAQModel] Match fuzzy trouvé pour: '{norm_q}' (score={best_fuzzy_score})")
                return self.answers[best_fuzzy_idx]
        except ImportError:
            print("[MLFAQModel] rapidfuzz non installé, pas de fuzzy matching")
            return None
        return None

    def reload(self):
        """Recharge"""
        self._loaded = False
        self._ensure_loaded()
