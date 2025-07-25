
import os
import json
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    raise ImportError("scikit-learn n'est pas installé. Installez-le avec 'pip install scikit-learn'.")

class MLFAQModel:
    def _fit_vectorizer(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer()
        self.question_vecs = self.vectorizer.fit_transform(self.questions)
    def _load_examples(self):
        self.questions = []
        self.answers = []
        import glob
        import json
        import os
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/enrichissement'))
        files = glob.glob(os.path.join(data_dir, 'enrichissement*.jsonl'))
        for file in files:
            with open(file, encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                        norm_q = self.normalize(obj['input'])
                        if self.debug:
                            print(f"[MLFAQModel] Ajout exemple: '{obj['input']}' => '{norm_q}' (depuis {os.path.basename(file)})")
                        self.questions.append(norm_q)
                        self.answers.append(obj['target'])
                    except Exception as e:
                        if self.debug:
                            print(f"[MLFAQModel] Erreur chargement exemple: {e} (fichier {os.path.basename(file)})")
                        continue
    """
    Modèle ML local basé sur la similarité TF-IDF pour Q&A, 100% offline.
    Il utilise un fichier JSONL d'exemples (input/target) pour répondre aux questions proches.
    """
    def __init__(self, data_path=None, debug=True):
        # Toujours initialiser self.debug pour éviter les erreurs d'attribut
        self.debug = debug
        if data_path is None:
            data_path = os.path.join(os.path.dirname(__file__), '../data/enrichissement_exemples.jsonl')
        self.data_path = os.path.abspath(data_path)
        self.questions = []
        self.answers = []
        self.vectorizer = TfidfVectorizer()
        self._load_examples()
        self._fit_vectorizer()

    @staticmethod
    def normalize(text):
        # Minuscule, suppression accents, ponctuation, mais garde les espaces pour le matching naturel
        import unicodedata
        text = text.lower()
        text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
        # Remplace toute ponctuation/séparateur par un espace, mais garde les mots séparés
        text = ''.join(c if not (unicodedata.category(c).startswith('P') or unicodedata.category(c).startswith('Z')) else ' ' for c in text)
        text = ' '.join(text.split())  # Un seul espace entre chaque mot
        return text

    def predict(self, question, threshold=0.5):
        """
        Retourne la réponse la plus proche si la similarité est suffisante, sinon None.
        Ajoute un bypass exact-match et un fallback fuzzy (rapidfuzz).
        Ajoute des logs détaillés pour la normalisation.
        """
        # Seuils plus stricts
        threshold = 0.7
        seuil_fuzzy = 92
        norm_q = self.normalize(question)
        if self.debug:
            print(f"[MLFAQModel] Question posée: '{question}' => normalisée: '{norm_q}'")

        # 1. Bypass exact-match
        for idx, q in enumerate(self.questions):
            if norm_q == q:
                if self.debug:
                    print(f"[MLFAQModel] Exact match trouvé pour '{norm_q}' (index {idx})")
                return self.answers[idx]

        # 2. TF-IDF similarity
        vec = self.vectorizer.transform([norm_q])
        sims = cosine_similarity(vec, self.question_vecs)[0]
        best_idx = sims.argmax()
        if sims[best_idx] >= threshold:
            if self.debug:
                print(f"[MLFAQModel] Réponse FAQ trouvée: {self.answers[best_idx]}")
            return self.answers[best_idx]

        # 3. Fallback fuzzy matching (rapidfuzz)
        try:
            from rapidfuzz import fuzz
            fuzzy_scores = [fuzz.ratio(norm_q, q) for q in self.questions]
            best_fuzzy_idx = int(max(range(len(fuzzy_scores)), key=lambda i: fuzzy_scores[i]))
            best_fuzzy_score = fuzzy_scores[best_fuzzy_idx]
            if best_fuzzy_score >= seuil_fuzzy:
                if self.debug:
                    print(f"[MLFAQModel] Réponse FAQ fuzzy trouvée: {self.answers[best_fuzzy_idx]}")
                return self.answers[best_fuzzy_idx]
        except ImportError:
            if self.debug:
                print("[MLFAQModel] rapidfuzz non installé, fuzzy matching désactivé.")
        return None

    def reload(self):
        self._load_examples()
        self._fit_vectorizer()
