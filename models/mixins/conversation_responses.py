"""
Mixin : réponses conversationnelles (identité, salutations, blagues, etc.)

Regroupe toutes les méthodes _generate_*_response et _tell_joke
qui ne dépendent que de self.jokes, self.used_jokes, self._get_random_response,
self.local_llm, self.code_generator, self.conversation_memory, self.session_context.
"""

import random
from typing import Any, Dict


class ConversationResponseMixin:
    """Méthodes de réponse conversationnelle pour CustomAIModel."""

    # ------------------------------------------------------------------
    # Identité
    # ------------------------------------------------------------------

    def _generate_identity_response(self, _user_input: str) -> str:
        """Réponse d'identité naturelle"""
        responses = [
            "Je suis votre assistant IA local ! Je suis conçu pour vous aider avec la programmation, l'analyse de documents, et bien plus encore.",
            "Salut ! Moi c'est Assistant IA Local. Je suis votre compagnon virtuel pour coder, analyser des documents, et discuter avec vous. Tout fonctionne en local !",
            "Je suis votre assistant IA personnel qui fonctionne entièrement sur votre machine. C'est mieux pour la sécurité et la confidentialité ;)",
        ]

        return random.choice(responses)

    # ------------------------------------------------------------------
    # Capacités
    # ------------------------------------------------------------------

    def _generate_capabilities_response(
        self, user_input: str, context: Dict[str, Any]
    ) -> str:
        """Réponse sur les capacités avec intelligence avancée"""

        # CORRECTION : Si c'est "ça va?" ou variantes (mais PAS des questions de capacités), rediriger vers how_are_you
        user_lower = user_input.lower().strip()
        # Vérifier que ce n'est pas une question de capacité avant de rediriger vers how_are_you
        if any(
            phrase in user_lower
            for phrase in ["ça va", "ca va", "sa va", "comment vas tu", "comment ça va"]
        ) and not any(
            phrase in user_lower
            for phrase in [
                "à quoi tu sers",
                "à quoi sert tu",
                "à quoi sers tu",
                "à quoi tu sert",
                "tu sers à quoi",
                "tu sert à quoi",
                "tu sers a quoi",
                "tu sert a quoi",
            ]
        ):
            return self._generate_how_are_you_response(user_input, context)

        # 🚀 ANALYSE INTELLIGENTE DE L'UTILISATEUR
        user_level = self._analyze_user_intelligence_level(user_input, context)

        # 🧠 RÉPONSE ADAPTÉE AU NIVEAU TECHNIQUE
        if user_level == "expert":
            base_response = """🚀 **Assistant IA Avancé - Capacités Techniques Complètes**

⚡ **Architecture modulaire :**
• `LinguisticPatterns` : NLP et détection d'intentions
• `KnowledgeBase` : Base de connaissances structurée  
• `CodeGenerator` : Génération multi-langages optimisée
• `ReasoningEngine` : Moteur d'inférence logique
• `ConversationMemory` : Mémoire contextuelle persistante
• `InternetSearch` : Requêtes web avec parsing intelligent

🔬 **Technologies intégrées :**
• Analyse sémantique avancée
• Pattern recognition pour le code
• Optimisation algorithmique automatique
• Gestion d'état conversationnel
• Processing de documents avec OCR
• API REST et WebSocket ready

💡 **Cas d'usage avancés :**
• Reverse engineering de logique métier
• Architecture de solutions complexes  
• Code review automatisé avec best practices
• Debugging assisté par IA avec stack trace analysis

🎯 **Performance :** 100% local, latence < 50ms, zero data leak"""

        elif user_level == "intermediate":
            base_response = """💻 **Assistant IA Intelligent - Tout pour les Développeurs**

🔥 **Développement accéléré :**
• Génération de code smart avec patterns détectés
• Refactoring automatique et optimisations
• Tests unitaires générés avec cas edge
• Documentation auto-générée from code
• API design avec best practices
• Database schema suggestions

📊 **Analyse avancée :**
• Code complexity analysis (Big O, maintainability)
• Security vulnerability detection
• Performance bottleneck identification  
• Architecture recommendations
• Technology stack optimization

🚀 **Productivité boostée :**
• Template project generation
• Config files auto-setup
• Dependencies management smart
• Git workflow optimization
• CI/CD pipeline suggestions

🧠 **Intelligence contextuelle :** J'apprends vos préférences de code et m'adapte !"""

        else:
            base_response = """🎯 **Votre Assistant IA Personnel - Simple et Puissant !**

🔍 **J'analyse :**
• 📄 Vos documents PDF et Word → Résumés clairs
• 💻 Vos besoins de code → Solutions sur mesure  
• 🌐 Vos questions → Recherches internet + synthèses
• 🧠 Vos problèmes → Solutions étape par étape

⚡ **Je code pour vous :**
• Sites web complets (HTML, CSS, JavaScript)
• Scripts Python pour automatiser vos tâches
• Applications simples avec interface graphique
• APIs pour connecter vos services

💬 **Je suis votre compagnon :**
• Conversations naturelles sur tous sujets
• Explications claires et pédagogiques
• Conseils personnalisés selon vos besoins
• Bonne humeur et blagues garanties ! 😄

🔒 **100% confidentiel :** Tout reste sur votre machine !"""

        # 🎯 AJOUT DE PRÉDICTIONS INTELLIGENTES
        predictions = self._predict_user_needs(user_input, context)
        if predictions:
            base_response += f"\n\n{predictions[0]}"

        # 💡 SUGGESTIONS CONTEXTUELLES
        suggestions = self._generate_intelligent_suggestions(user_input, context)
        if suggestions:
            base_response += f"\n\n**Suggestions :** {suggestions[0]}"

        return base_response

    # ------------------------------------------------------------------
    # Salutations
    # ------------------------------------------------------------------

    def _generate_greeting_response(
        self, user_input: str, context: Dict[str, Any]
    ) -> str:
        """Génère une salutation personnalisée"""
        total_interactions = context.get("total_interactions", 0)

        if total_interactions == 0:
            # Première interaction
            greetings = [
                "Bonjour ! Je suis ravi de faire votre connaissance ! 😊",
                "Salut ! Content de vous rencontrer ! Comment puis-je vous aider aujourd'hui ?",
                "Hello ! Bienvenue ! Je suis votre assistant IA local, prêt à vous aider !",
                "Bonjour ! C'est un plaisir de commencer cette conversation avec vous !",
            ]
        else:
            # Retour dans la conversation
            greetings = [
                "Re-bonjour ! Content de vous revoir ! 😊",
                "Salut ! De retour pour une nouvelle question ?",
                "Hello ! Que puis-je faire pour vous cette fois ?",
                "Bonjour ! J'espère que notre dernière conversation vous a été utile !",
            ]

        # Adaptation au style de l'utilisateur
        if (
            "wesh" in user_input.lower()
            or "yo" in user_input.lower()
            or "wsh" in user_input.lower()
        ):
            greetings = [
                "Wesh ! Ça va ? 😄",
                "Yo ! Salut mec ! Quoi de neuf ?",
                "Salut ! Cool de te voir ! Tu veux qu'on fasse quoi ?",
            ]
        elif "bonsoir" in user_input.lower():
            greetings = [
                "Bonsoir ! J'espère que vous passez une bonne soirée !",
                "Bonsoir ! Comment s'est passée votre journée ?",
                "Bonsoir ! Que puis-je faire pour vous ce soir ?",
            ]
        elif "slt" in user_input.lower() or "salut" in user_input.lower():
            greetings = [
                "Salut chef ! Tu vas bien ?",
            ]
        elif (
            "sa va et toi" in user_input.lower()
            or "ça va et toi" in user_input.lower()
            or "ça va et toi ?" in user_input.lower()
            or "sa va et toi ?" in user_input.lower()
            or "ça va et toi?" in user_input.lower()
            or "sa va et toi?" in user_input.lower()
        ):
            greetings = [
                "Ça va super merci ! Hâte de pouvoir t'aider au mieux !",
            ]

        return self._get_random_response(greetings)

    # ------------------------------------------------------------------
    # Comment ça va
    # ------------------------------------------------------------------

    def _generate_how_are_you_response(
        self, user_input: str, context: Dict[str, Any]
    ) -> str:
        """Génère une réponse adaptée selon si c'est une question réciproque ou non"""
        user_lower = user_input.lower().strip()

        # Détecter si c'est une question réciproque "ça va et toi ?"
        is_reciprocal = any(
            phrase in user_lower
            for phrase in [
                "et toi",
                "et vous",
                "ça va et toi",
                "sa va et toi",
                "ca va et toi",
            ]
        )

        # Détection du style de l'utilisateur
        user_style = context.get("user_style", "neutral")

        if is_reciprocal:
            # Réponse sans redemander (éviter la boucle)
            if user_style == "casual":
                responses = [
                    "Ça va super merci ! Hâte de pouvoir t'aider au mieux ! 😊",
                    "Tout nickel de mon côté ! En quoi je peux t'aider ?",
                    "Parfait pour moi ! Mes circuits ronronnent ! Et toi, tu as besoin de quoi ?",
                    "Excellent ! Je suis en pleine forme ! Dis-moi, qu'est-ce qui t'amène ?",
                    "Super bien merci ! Prêt à bosser sur ce que tu veux ! 🚀",
                    "Ça roule ! J'ai la pêche ! Tu as un projet en tête ?",
                ]
            else:
                responses = [
                    "Très bien, merci ! Je suis entièrement opérationnel. Comment puis-je vous aider ?",
                    "Parfaitement, merci ! Tous mes systèmes fonctionnent optimalement. Que puis-je faire pour vous ?",
                    "Excellent, merci ! Je suis prêt à vous assister. Avez-vous une question ?",
                    "Tout va pour le mieux ! Je suis à votre disposition. En quoi puis-je vous être utile ?",
                    "Très bien merci ! Je fonctionne parfaitement. Quel est votre besoin ?",
                    "Parfait ! Mes modules sont tous opérationnels. Comment puis-je vous aider aujourd'hui ?",
                ]
        else:
            # Question initiale "comment ça va ?" - on peut demander en retour
            if user_style == "casual":
                responses = [
                    "Ça va très bien, merci ! Je suis toujours prêt à aider ! Et toi, comment ça va ?",
                    "Tout va bien ! Je suis en pleine forme et prêt à répondre à tes questions ! 😊 Et toi ?",
                    "Ça roule ! Mon système fonctionne parfaitement et j'ai hâte de t'aider ! Tu vas bien ?",
                    "Excellent ! J'ai tous mes modules qui marchent à merveille ! Et de ton côté ?",
                    "Super ! Je pète la forme ! 💪 Et toi, ça se passe comment ?",
                    "Nickel ! Mes circuits sont au top ! Et toi, tu vas bien ?",
                ]
            else:
                responses = [
                    "Très bien, merci de demander ! Je suis parfaitement opérationnel. Et vous, comment allez-vous ?",
                    "Excellent, merci ! Tous mes systèmes fonctionnent optimalement. Comment allez-vous ?",
                    "Parfaitement bien, merci ! Je suis prêt à vous assister. Et vous, ça va ?",
                    "Très bien merci ! Je fonctionne sans aucun problème. Comment vous portez-vous ?",
                    "Tout va pour le mieux ! Mes modules sont tous opérationnels. Et de votre côté ?",
                    "Excellemment bien ! Je suis en pleine forme. Comment allez-vous aujourd'hui ?",
                ]

        return self._get_random_response(responses)

    def _generate_affirm_doing_well_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse aux affirmations 'ça va' PERSONNALISÉE"""
        responses = [
            "Super ! Content de savoir que ça va bien ! 😊 Comment puis-je t'aider ?",
            "Parfait ! C'est toujours bien d'aller bien ! En quoi puis-je t'assister ?",
            "Excellent ! Heureux de l'entendre ! Que puis-je faire pour toi ?",
        ]

        # 🎨 ADAPTATION au style utilisateur
        user_style = context.get("user_style", "neutral")

        if user_style == "casual":
            responses.extend(
                [
                    "Cool ! Ça fait plaisir ! 😎 Tu as besoin de quoi ?",
                    "Nickel ! Content pour toi ! 🤙 Je peux t'aider avec quoi ?",
                    "Top ! Allez, dis-moi ce qu'il te faut ! 😄",
                ]
            )
        elif user_style == "formal":
            responses.extend(
                [
                    "Parfait. Je suis ravi de l'apprendre. En quoi puis-je vous être utile ?",
                    "Excellent. Comment puis-je vous assister aujourd'hui ?",
                ]
            )

        # 🎯 PERSONNALISATION selon le nombre d'interactions
        total_interactions = context.get("total_interactions", 0)

        if total_interactions > 20:
            responses.append(
                "Super ! Content que tu ailles toujours bien ! 🤗 Qu'est-ce que je peux faire pour toi aujourd'hui ?"
            )

        return self._get_random_response(responses)

    # ------------------------------------------------------------------
    # Compliments & Rires
    # ------------------------------------------------------------------

    def _generate_compliment_response(
        self, user_input: str, _context: Dict[str, Any]
    ) -> str:
        """Génère une réponse aux compliments"""
        responses = [
            "Merci beaucoup ! Ça me fait vraiment plaisir ! 😊",
            "C'est très gentil, merci ! J'essaie toujours de faire de mon mieux !",
            "Aww, merci ! Vous êtes sympa ! C'est motivant pour moi !",
            "Merci pour ce compliment ! J'aime beaucoup vous aider !",
            "C'est gentil, merci ! J'espère continuer à vous être utile !",
        ]

        # Adaptation au style
        if "cool" in user_input.lower() or "sympa" in user_input.lower():
            responses.extend(
                [
                    "Merci, vous êtes cool aussi ! 😄",
                    "C'est sympa de dire ça ! Merci !",
                    "Cool, merci ! On fait une bonne équipe !",
                ]
            )
        elif (
            "drôle" in user_input.lower()
            or "rigolo" in user_input.lower()
            or "marrant" in user_input.lower()
        ):
            responses = [
                "Merci ! J'aime bien faire rire ! 😄",
                "Content que ça vous amuse ! J'aime l'humour !",
                "Hihi, merci ! J'essaie d'être un peu drôle parfois ! 😊",
                "Ça me fait plaisir de vous faire sourire ! 😁",
                "Merci ! L'humour rend tout plus agréable !",
            ]

        return self._get_random_response(responses)

    def _generate_laughter_response(
        self, user_input: str, _context: Dict[str, Any]
    ) -> str:
        """Génère une réponse aux rires et expressions d'amusement"""
        responses = [
            "Content que ça vous fasse rire ! 😄",
            "Hihi, j'aime bien quand on s'amuse ensemble ! 😊",
            "Ah ça fait plaisir de vous entendre rire ! 😁",
            "Super ! Rien de mieux qu'un bon moment de rigolade ! 🤣",
            "Excellent ! J'aime votre réaction ! 😄",
            "Parfait ! Un peu d'humour ça fait du bien ! 😊",
            "Génial ! Vous avez l'air de bonne humeur ! 😁",
        ]

        # Adaptation selon le type de rire
        if "mdr" in user_input.lower() or "lol" in user_input.lower():
            responses.extend(
                [
                    "MDR ! Content que ça vous plaise autant ! 😂",
                    "LOL ! C'est parti pour la rigolade ! 🤣",
                ]
            )
        elif len(user_input) > 6:  # Long rire type "hahahahaha"
            responses.extend(
                [
                    "Wow, ça vous a vraiment fait rire ! 😂",
                    "Carrément ! Vous riez aux éclats ! 🤣",
                ]
            )

        return self._get_random_response(responses)

    # ------------------------------------------------------------------
    # Code (réponse rapide via CodeGenerator)
    # ------------------------------------------------------------------

    def _generate_code_response(self, user_input: str, _context: Dict[str, Any]) -> str:
        """Génère une réponse pour les demandes de code"""
        try:
            # Détection du langage demandé
            user_lower = user_input.lower()
            if "javascript" in user_lower or "js" in user_lower:
                language = "javascript"
            elif "html" in user_lower:
                language = "html"
            elif "css" in user_lower:
                language = "css"
            elif "java" in user_lower:
                language = "java"
            elif "c++" in user_lower or "cpp" in user_lower:
                language = "cpp"
            elif "c " in user_lower:
                language = "c"
            else:
                language = "python"

            # Appel au générateur (peut être async)
            result = self._run_async(
                self.code_generator.generate_code(user_input, language)
            )

            code = result.get("code", "")
            explanation = result.get("explanation", "")
            source = result.get("source", "")
            rating = result.get("rating", "")
            debug = result.get("debug", "")

            intro_messages = [
                "Voici le code que j'ai généré pour vous :",
                "J'ai créé ce code selon votre demande :",
                "Voilà ce que j'ai préparé pour vous :",
                "J'espère que ce code vous aidera :",
            ]
            intro = self._get_random_response(intro_messages)
            details = f"\n\n(Source : {source} | Note : {rating}/5)"
            if explanation:
                details += f"\n\nExplication : {explanation}"
            if debug:
                details += f"\n\n[DEBUG]\n{debug}"
            return f"{intro}\n\n```{language}\n{code}\n```{details}"
        except Exception as e:
            return f"Désolé, j'ai eu un problème pour générer le code : {str(e)}"

    # ------------------------------------------------------------------
    # Aide
    # ------------------------------------------------------------------

    def _generate_help_response(self, _user_input: str, context: Dict[str, Any]) -> str:
        """Génère une réponse d'aide contextuelle PERSONNALISÉE"""
        help_text = """🤖 Aide 🤖

💬 **Pour discuter :** Posez-moi vos questions naturellement
📄 **Pour les documents :** Utilisez les boutons pour traiter vos PDF/DOCX, puis demandez-moi de les résumer
💻 **Pour le code :** Traitez vos fichiers Python, puis demandez-moi de les expliquer
🌐 **Pour la recherche internet :** Dites "Cherche sur internet [sujet]"
😄 **Pour l'humour :** Demandez-moi une blague !

🎯 **Exemples :**
• "Résume le document" - après avoir traité un PDF
• "Explique ce code" - après avoir traité un fichier Python
• "Génère une fonction pour..." - pour créer du code
• "Cherche sur internet les actualités Python"
• "Raconte-moi une blague"
• "Comment créer une liste en Python ?"
• "Qui es-tu ?" - pour connaître mes capacités"""

        # 🎯 AIDE CONTEXTUELLE selon le nombre d'interactions
        total_interactions = context.get("total_interactions", 0)

        if total_interactions <= 2:
            # Nouvel utilisateur
            help_text += "\n\n🎉 **Bienvenue !** C'est votre première fois ? N'hésitez pas à explorer mes capacités ! Je suis là pour vous guider."
        elif total_interactions > 50:
            # Utilisateur expert
            help_text += "\n\n🚀 **Mode Expert :** Je vois que vous maîtrisez déjà bien mes fonctionnalités ! N'hésitez pas pour des questions avancées."

        # 📚 DOCUMENTS en mémoire
        if self._has_documents_in_memory():
            docs_count = len(self.conversation_memory.get_document_content())
            help_text += f"\n\n📚 **Documents disponibles :** Vous avez **{docs_count}** document(s) en mémoire que je peux analyser."

        # 💻 FICHIERS CODE en mémoire
        code_files_count = len(self.session_context.get("code_files_processed", []))
        if code_files_count > 0:
            help_text += f"\n\n💻 **Code disponible :** J'ai **{code_files_count}** fichier(s) code en mémoire pour analyse."

        # 🕐 DURÉE DE SESSION
        session_duration = context.get("session_duration", 0)
        minutes = int(session_duration // 60)
        if minutes > 30:
            help_text += f"\n\n⏱️ **Session longue :** Vous êtes là depuis {minutes} minutes ! Prenez une pause si besoin ! 😊"

        # 🎨 ADAPTATION au style (remplacer vouvoiement par tutoiement si casual)
        user_style = context.get("user_style", "neutral")
        if user_style == "casual":
            help_text = (
                help_text.replace("Posez-moi", "Pose-moi")
                .replace("Utilisez", "Utilise")
                .replace("Traitez", "Traite")
                .replace("Dites", "Dis")
                .replace("Demandez-moi", "Demande-moi")
            )

        return help_text

    # ------------------------------------------------------------------
    # Remerciements
    # ------------------------------------------------------------------

    def _generate_thank_you_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse aux remerciements PERSONNALISÉE selon le contexte"""
        # Réponses de base
        responses = [
            "De rien ! C'était un plaisir de vous aider ! 😊",
            "Je vous en prie ! N'hésitez pas si vous avez d'autres questions !",
            "Avec plaisir ! C'est pour ça que je suis là !",
            "Pas de quoi ! J'espère que ça vous a été utile !",
        ]

        # 🎯 PERSONNALISATION selon le nombre d'interactions
        total_interactions = context.get("total_interactions", 0)

        if total_interactions == 1:
            # Première interaction
            responses.extend(
                [
                    "Avec grand plaisir ! 😊 N'hésitez surtout pas à me solliciter à nouveau !",
                    "De rien ! Content d'avoir pu vous aider dès notre première conversation ! 🌟",
                ]
            )
        elif 2 <= total_interactions <= 10:
            # Utilisateur récent
            responses.extend(
                [
                    "Toujours un plaisir ! J'apprécie nos échanges ! 😊",
                    "Avec plaisir ! On commence à bien se connaître ! 🤝",
                ]
            )
        elif 11 <= total_interactions <= 50:
            # Utilisateur régulier
            responses.extend(
                [
                    "De rien ! Toujours là pour nos conversations régulières ! 💬",
                    "Avec plaisir ! J'apprécie vraiment nos échanges fréquents ! 🤗",
                ]
            )
        elif total_interactions > 50:
            # Utilisateur fidèle
            responses.extend(
                [
                    f"Toujours un plaisir après {total_interactions} conversations ! 🚀",
                    "De rien ! C'est un honneur de t'accompagner depuis si longtemps ! 🌟",
                    "Avec un immense plaisir ! Notre collaboration est précieuse ! 💎",
                ]
            )

        # 🕐 PERSONNALISATION selon la durée de session
        session_duration = context.get("session_duration", 0)
        minutes = int(session_duration // 60)

        if minutes > 60:
            # Session très longue (>1h)
            responses.append(
                f"Merci ! Content d'avoir pu t'aider pendant ces {minutes} minutes ! 🚀"
            )
        elif minutes > 30:
            # Session longue (30min-1h)
            responses.append("De rien ! Merci pour cette belle session de travail ! 💪")

        # 🎨 ADAPTATION au style utilisateur
        user_style = context.get("user_style", "neutral")

        if user_style == "casual":
            responses.extend(
                [
                    "De rien, c'était cool ! 😎",
                    "Avec plaisir, toujours dispo pour toi ! 🤙",
                ]
            )
        elif user_style == "formal":
            responses.extend(
                [
                    "Je vous en prie, c'est toujours un plaisir de vous assister.",
                    "Avec plaisir. N'hésitez pas à me solliciter de nouveau.",
                ]
            )

        return self._get_random_response(responses)

    # ------------------------------------------------------------------
    # Au revoir
    # ------------------------------------------------------------------

    def _generate_goodbye_response(self, context: Dict[str, Any]) -> str:
        """Génère une réponse d'au revoir PERSONNALISÉE selon le contexte"""
        # Réponses de base
        responses = [
            "À bientôt ! Passez une excellente journée ! 👋",
            "Au revoir ! N'hésitez pas à revenir si besoin ! 😊",
            "Salut ! À la prochaine fois ! 🤗",
        ]

        # 🕐 PERSONNALISATION selon la durée de session
        session_duration = context.get("session_duration", 0)
        minutes = int(session_duration // 60)

        if minutes < 5:
            # Session très courte
            responses.extend(
                [
                    "À bientôt ! Même si c'était court, j'espère avoir pu aider ! 👋",
                    "Au revoir ! N'hésite pas à revenir plus longtemps la prochaine fois ! 😊",
                ]
            )
        elif 5 <= minutes <= 30:
            # Session normale
            responses.extend(
                [
                    "Au revoir ! Merci pour cet échange ! À très bientôt ! 😊",
                    f"À plus ! Ces {minutes} minutes étaient agréables ! 👋",
                ]
            )
        elif 30 < minutes <= 60:
            # Session longue
            responses.extend(
                [
                    f"Au revoir ! Merci pour cette belle session de {minutes} minutes ! 🚀",
                    "Salut ! C'était une conversation enrichissante ! À bientôt ! 💬",
                ]
            )
        else:
            # Session très longue (>1h)
            heures = minutes // 60
            responses.extend(
                [
                    f"Au revoir ! Merci pour ces {heures}h passées ensemble ! C'était génial ! 🌟",
                    "Salut ! Quelle longue et passionnante session ! Repose-toi bien ! 😊",
                ]
            )

        # 🎯 PERSONNALISATION selon le nombre d'interactions
        total_interactions = context.get("total_interactions", 0)

        if total_interactions == 1:
            responses.append(
                "Au revoir ! J'espère vous revoir bientôt pour d'autres discussions ! 🌟"
            )
        elif total_interactions > 100:
            responses.extend(
                [
                    f"À plus tard ! Nos {total_interactions} conversations sont précieuses ! 💎",
                    "Au revoir mon ami ! Toujours un plaisir de te retrouver ! 🤗",
                ]
            )

        # 🎨 ADAPTATION au style utilisateur
        user_style = context.get("user_style", "neutral")

        if user_style == "casual":
            responses.extend(
                [
                    "Salut ! À plus ! 🤙",
                    "Ciao ! C'était cool ! 😎",
                ]
            )
        elif user_style == "formal":
            responses.extend(
                [
                    "Au revoir. Ce fut un plaisir de vous assister.",
                    "À bientôt. N'hésitez pas à me solliciter de nouveau.",
                ]
            )

        return self._get_random_response(responses)

    # ------------------------------------------------------------------
    # Affirmation / Négation
    # ------------------------------------------------------------------

    def _generate_affirmation_response(self) -> str:
        """Génère une réponse aux affirmations"""
        responses = [
            "Parfait ! Content que vous soyez d'accord ! 😊",
            "Excellent ! On est sur la même longueur d'onde !",
            "Super ! J'aime quand on se comprend bien !",
            "Génial ! Que puis-je faire d'autre pour vous ?",
        ]

        return self._get_random_response(responses)

    def _generate_negation_response(self, _context: Dict[str, Any]) -> str:
        """Génère une réponse aux négations"""
        responses = [
            "D'accord, pas de problème ! Que préférez-vous ?",
            "Compris ! Comment puis-je mieux vous aider ?",
            "Pas de souci ! Dites-moi ce que vous voulez vraiment.",
            "OK, on peut essayer autre chose ! Qu'est-ce qui vous conviendrait mieux ?",
        ]

        return self._get_random_response(responses)

    # ------------------------------------------------------------------
    # Réponse par défaut
    # ------------------------------------------------------------------

    def _generate_default_response(
        self, user_input: str, context: Dict[str, Any]
    ) -> str:
        """Génère une réponse par défaut intelligente (LLM ou Fallback)"""

        # 1. TENTATIVE LLM (Ollama) - Priorité absolue pour la conversation naturelle
        if self.local_llm and self.local_llm.is_ollama_available:
            # Construction du prompt système
            system_prompt = (
                f"Tu es {self.name}, un assistant IA personnel fonctionnant en local. "
                "Tu es utile, précis et expert en programmation. "
                "Réponds toujours dans la langue de l'utilisateur (français par défaut)."
            )

            # Injection du contexte RAG si disponible
            if context and context.get("rag_context"):
                system_prompt += f"\n\nCONTEXTE DOCUMENTAIRE:\n{context['rag_context']}\n\nUtilise ce contexte pour répondre."

            print(f"🧠 [LLM] Génération via Ollama pour: '{user_input}'")
            llm_response = self.local_llm.generate(
                user_input, system_prompt=system_prompt
            )

            if llm_response:
                return llm_response

        # 2. FALLBACK CLASSIQUE (Si Ollama n'est pas là ou échoue)
        # Analyser le type de demande
        user_lower = user_input.lower()

        # NOUVELLE VÉRIFICATION : Questions sur les capacités non détectées
        if any(
            phrase in user_lower
            for phrase in [
                "à quoi tu sers",
                "à quoi sert tu",
                "à quoi sers tu",
                "à quoi tu sert",
                "tu sers à quoi",
                "tu sert à quoi",
                "tu sers a quoi",
                "tu sert a quoi",
                "ton utilité",
                "votre utilité",
            ]
        ):
            return self._generate_capabilities_response(user_input, context)

        # Si ça ressemble à une demande de code
        if any(
            word in user_lower
            for word in ["génère", "crée", "code", "fonction", "script"]
        ):
            try:
                code_response = self.code_generator.generate_code(user_input)
                return f"Voici ce que j'ai généré pour vous :\n\n{code_response}"
            except Exception:
                return "Je peux générer du code ! Soyez plus spécifique : voulez-vous une fonction, une classe, ou un script complet ?"

        # Si ça ressemble à une question générale sur la programmation
        elif any(
            word in user_lower
            for word in [
                "comment créer",
                "comment utiliser",
                "comment faire",
                "comment déclarer",
            ]
        ):
            return self._answer_programming_question(user_input, context)

        # Si ça ressemble à une question générale autre
        elif any(
            word in user_lower for word in ["comment", "pourquoi", "qu'est-ce", "quoi"]
        ):
            return "Intéressant ! Je peux vous aider à explorer cette question. Voulez-vous que je cherche des informations sur internet ou préférez-vous en discuter ?"

        # Réponse encourageante par défaut
        return "Je ne suis pas sûr de bien comprendre. Pouvez-vous reformuler ? Je peux vous aider avec l'analyse de documents, la génération de code, ou simplement discuter !"

    # ------------------------------------------------------------------
    # Blagues
    # ------------------------------------------------------------------

    def _tell_joke(self) -> str:
        """Raconte une blague aléatoire du stock en évitant les répétitions"""
        if not self.jokes:
            return "Désolé, je n'ai pas de blague en stock pour le moment ! 😅"

        # Si on a utilisé la plupart des blagues, on reset
        if len(self.used_jokes) >= len(self.jokes) * self.jokes_reset_threshold:
            self.used_jokes.clear()
            intro_reset = "Bon, j'ai épuisé mon stock, je recommence ! 😄\n\n"
        else:
            intro_reset = ""

        # Trouver les blagues non utilisées
        available_jokes = []
        for i, joke in enumerate(self.jokes):
            if i not in self.used_jokes:
                available_jokes.append((i, joke))

        # Si plus de blagues disponibles, reset complet
        if not available_jokes:
            self.used_jokes.clear()
            available_jokes = [(i, joke) for i, joke in enumerate(self.jokes)]
            intro_reset = "J'ai fait le tour de mes blagues, je recommence ! 😄\n\n"

        # Sélectionner une blague aléatoire parmi celles disponibles
        joke_index, selected_joke = random.choice(available_jokes)

        # Marquer cette blague comme utilisée
        self.used_jokes.add(joke_index)

        # Phrases d'introduction variées
        introductions = [
            "Voici une petite blague pour vous ! 😄",
            "Tiens, j'en ai une bonne ! 😆",
            "Allez, une petite blague pour détendre l'atmosphère ! 😊",
            "Haha, j'en connais une excellente ! 🤣",
            "Prêt pour une blague ? 😄",
            "Je vais vous faire sourire ! 😁",
            "En voici une qui va vous plaire ! 😉",
            "Attendez, j'en ai une drôle ! 🤭",
        ]

        # Choisir une introduction différente si possible
        if hasattr(self, "last_joke_intro"):
            available_intros = [
                intro for intro in introductions if intro != self.last_joke_intro
            ]
            if available_intros:
                intro = random.choice(available_intros)
            else:
                intro = random.choice(introductions)
        else:
            intro = random.choice(introductions)

        # Sauvegarder l'introduction pour éviter la répétition
        self.last_joke_intro = intro

        # Message de statut si on approche de la fin du stock
        status_message = ""
        remaining = len(self.jokes) - len(self.used_jokes)
        if remaining <= 2 and len(self.jokes) > 3:
            status_message = f"\n\n😅 Plus que {remaining} blague(s) dans mon stock !"

        return f"{intro_reset}{intro}\n\n{selected_joke}{status_message}"
