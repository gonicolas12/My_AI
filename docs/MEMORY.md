# 🧠 Mémoire — voir, éditer et supprimer ce que l'IA sait

My_AI mémorise des informations sur vous pour des réponses plus pertinentes. Comme **tout est local**, vous devez pouvoir **inspecter et reprendre le contrôle** de cette mémoire. Le panneau **Mémoire** (bouton en bas de la barre latérale) offre des opérations CRUD **réelles** sur les deux stores de mémoire — aucune donnée ne quitte votre machine, aucune suppression simulée.

---

## 📍 Où la trouver

Cliquez sur **Mémoire** en bas de la barre latérale (ou cherchez « Mémoire » dans la palette Ctrl+K) : le panneau s'ouvre dans la fenêtre.

> Le panneau Mémoire **remplace** l'ancienne mini-section « Connaissances » de la barre latérale : un seul endroit, plus complet (faits **et** mémoire vectorielle).

---

## 🗂️ Les deux stores de mémoire

| Store | Backend | Contenu | Onglet |
|---|---|---|---|
| **Faits structurés** | SQLite (`data/knowledge_base/facts.db`) | Faits catégorisés extraits/ajoutés (préférence, décision, personne, procédure, technique, général) | **Faits** |
| **Mémoire vectorielle — documents** | ChromaDB (`memory/vector_store/`) | Chunks des documents joints dans le chat ou ajoutés à la main ([détails](#-documents)) | **Documents** |
| **Mémoire vectorielle — conversations** | ChromaDB | Index de recherche reconstruit depuis vos conversations | **Conversations** |

---

## 🌍 Recherche multilingue

La mémoire vectorielle (onglets **Documents** et **Conversations**, outil `search_memory`, recherche globale, dossiers attachés) cherche par le **sens**, avec un modèle d'embeddings local : **Granite Embedding 107M multilingue** (IBM, Apache 2.0, 228 Mo), celui qui choisit déjà les passages des longs documents. Une question en français retrouve un passage anglais, arabe ou chinois.

| Modèle | 3 bons passages retrouvés | Vitesse |
|---|---|---|
| all-MiniLM-L6-v2 (avant, entraîné pour l'anglais) | 28 % | référence |
| **Granite 107M multilingue** (par défaut) | **76 %** | identique |

*29 questions en 9 langues sur la documentation française et anglaise de My_AI (10/11/2026). EmbeddingGemma 2 via Ollama faisait 76 à 79 %, dix fois plus lentement et 0,5 Go sur le GPU : non retenu.*

- **Réglage** : `optimization.rag.embedding_model` dans `config.yaml` (un modèle sentence-transformers du Hub Hugging Face, ou un dossier local).
- **Une collection par modèle** : les vecteurs de deux modèles ne se comparent pas, même à dimension égale. Chaque modèle a donc ses collections ChromaDB (`documents__granite-embedding-107m-multiling-8e8c41d0__384`…) ; MiniLM garde les noms historiques (`documents`, `conversations`, `codebase`).
- **Réindexation en arrière-plan** : au premier lancement avec un autre modèle, les entrées existantes sont recalculées depuis leur texte stocké (déchiffré pour le calcul, toujours chiffré dans la base), avec les mêmes identifiants et la même provenance. Pendant ce temps, la recherche ne voit que ce qui est déjà recalculé ; ce que vous supprimez ou modifiez l'est aussi dans l'ancienne collection, et rien ne revient. L'ancienne collection n'est supprimée qu'à la fin : appli fermée avant, la copie reprend au lancement suivant. Comptez quelques minutes pour plusieurs milliers d'entrées.
- **Repli** : tant que Granite n'est pas téléchargé (il l'est en arrière-plan au lancement), MiniLM sert la session avec l'index MiniLM ; Granite prend le relais au lancement suivant.
- **Morceaux** : 256 tokens, 32 de chevauchement (`optimization.rag.chunk_size` / `chunk_overlap`). Granite lit jusqu'à 512 tokens, mais retrouve mieux à 256 (76 % contre 62 % à 512).
- **Reranking multilingue** : avec Granite, `mmarco-mMiniLMv2` (14 langues, 470 Mo, téléchargé une fois en arrière-plan) remet les passages candidats dans l'ordre : 86 % de bons passages parmi les 3 retenus, contre 77 % avec Granite seul et 60 % avec l'ancien reranker anglais. Réglage : `optimization.rag.reranker_model` (`"auto"`, `"none"` ou un modèle).
- **Recherche des conversations** : un message est gardé s'il est assez proche de la question pour Granite (distance ≤ 0,32) ou s'il en contient tous les mots ; 17 questions sur 18 trouvent leur message, souvent écrit dans une autre langue, et une question hors sujet ne ramène rien.

---

## 💬 Mémoriser depuis le chat

Dites-le simplement dans la conversation, dans la fenêtre comme sur le téléphone :

> Retiens que mon chat s'appelle Félix.

Le fait est enregistré aussitôt dans l'onglet **Faits** (source : `conversation`), un indicateur « 🧠 Mémorisé : … » s'affiche, et My_AI le confirme dans sa réponse. Il reste disponible dans les conversations suivantes.

- **Formulations reconnues**, en début de message ou de phrase : « retiens que… », « retiens ceci : … », « souviens-toi que… », « n'oublie pas que… », « mémorise… », « garde en tête que… », « prends note que… », « tu peux retenir que… ? », et en anglais « remember that… », « keep in mind that… ». Les dix autres langues de l'appli ont les leurs : « Recuerda que vivo en Madrid », « Merk dir, dass… », « Ricordati che… », « Lembra que… », « Onthoud dat… », « Запомни, что… », « 记住… », « …と覚えておいて », « …기억해 줘 », « تذكر أن… ». Ce qui est retenu garde vos mots, même quand le modèle les traduit ; après un renvoi (« 记住这个 »), c'est votre dernière information.
- **Le modèle lit ce que vous demandez** : comme dans la conversation Code, le modèle du chat lit quoi retenir, remplacer ou oublier, avec les derniers échanges et les faits déjà retenus, en un appel court avant sa réponse, qui le confirme. « Retiens ça », juste après « mon frère s'appelle Paul », retient « mon frère s'appelle Paul », même si la réponse d'avant disait l'avoir déjà enregistré : un fait déjà retenu dont ni votre message ni les échanges ne parlent n'est pas repris, et une demande dont rien n'a pu être lu est relue sur vos seuls messages. « Retiens que mon chat s'appelle Félix. Quel temps fait-il ? » enregistre seulement « mon chat s'appelle Félix », puis répond à la question. Un bloc « Retiens ceci : … » est gardé en entier, avec vos mots, consignes comprises (une procédure, par exemple). S'il ne sait pas quoi retenir (« retiens ça » en tout début de conversation), rien n'est enregistré, et il vous le demande au lieu de répondre « c'est noté ». Sans Ollama, ou si cet appel échoue, des règles lisent les « retiens que… » comme avant.
- **Oublier, remplacer** : « Oublie que j'habite à Lyon » (ou « ne retiens plus que… », « supprime de ta mémoire… », « forget that… ») retire ce fait ; « non, retiens plutôt que j'habite à Nantes » met le nouveau à la place de l'ancien. Un indicateur « 🧠 Oublié : … » montre chaque fait retiré. La demande vise aussi les faits du code (« oublie que je fais mes tests avec pytest »). Chaque fait que le modèle retirerait est confirmé par un second appel court, qui vérifie que votre message le vise bien : seul, le modèle retirait parfois un fait sans rapport (« oublie que j'ai un chien » retirait votre prénom). Ce qui n'est pas dans la mémoire n'est pas inventé : rien n'est retiré, et My_AI vous le dit. Si votre message ne demande rien d'autre (« Oublie que j'ai un chien »), la réponse vient sans le modèle : « Je n'avais rien retenu là-dessus : il n'y a rien à oublier. » Le modèle répondait sinon « C'est noté : j'ai oublié que tu as un chien », juste après d'autres confirmations. Si le nouveau fait d'un remplacement ne peut pas être gardé, l'ancien reste. Une demande qui ne dit rien d'autre reçoit une courte confirmation, sans outils. Dans les autres langues : « Olvida que… », « Vergiss, dass… », « Забудь, что… », « 忘掉… », « …は忘れて », « …잊어 줘 », « انس أن… » ; « No olvides », « Vergiss nicht » ou « 忘れないで » demandent au contraire de retenir. La confirmation, comme la phrase « rien à oublier », vient dans la langue de votre message ; une demande qui ne dit rien d'autre y reçoit une phrase toute faite (« Anotado, lo recordaré. », « Hecho, lo he olvidado. »), et l'indicateur montre le fait.
- **Sans « retiens »** : ce que vous dites de durable sur vous (votre nom, vos proches, votre métier, où vous vivez, les langues que vous parlez, vos goûts, vos habitudes) ou sur la façon dont vous voulez qu'il vous réponde (langue, ton, longueur) est retenu de lui-même. « Je suis végétarien depuis dix ans, tu as une recette ? » retient « je suis végétarien depuis dix ans », et un indicateur « 🧠 Mémorisé » le montre à la fin de la réponse. Ce que vous dites de vous est gardé avec vos mots, même quand le message finit par une question : « Je travaille de nuit, tu as des conseils pour dormir ? » retient « je travaille de nuit ». Le modèle lit votre message pendant qu'il vous répond : la réponse n'attend pas. Il ne retient ni ce que vous lui demandez de faire, ni une question, ni ce que vous cherchez (« je cherche un roman en espagnol pour ma sœur »), ni ce qui ne vaut que pour l'instant (« je suis fatigué ce soir »), ni ce que dit un texte que vous collez, ni un code ou un mot de passe (dites « retiens ça » pour le garder), et dans le doute, rien. Ce qui contredit un fait déjà retenu (« j'ai déménagé à Nantes ») le remplace, une fois confirmé par le second appel ; ce qui s'y ajoute (« j'ai adopté un deuxième chat ») ne retire rien, et sans demande, rien d'autre n'est retiré. Ne sont pas lus : un message de moins de trois mots (« ok merci »), ou de deux dans les dix autres langues de l'appli, où « Я врач » ou « Soy médico » dit ce que « je suis médecin » dit en trois (en chinois et en japonais, écrits sans espaces, deux caractères comptent pour un mot) ; un texte de plus de 1 500 caractères ; une commande « /… » de la bibliothèque de prompts. Dans ces dix langues, ce qui est retenu est repris des parties de votre message qui le disent, sans votre question ni votre demande : « Я работаю медсестрой по ночам, посоветуй, как лучше спать днём? » retient « Я работаю медсестрой по ночам ». Le modèle, dont les consignes sont en français, l'aurait sinon écrit en français.
- **Seul votre message compte** : jamais une page web, un fichier lu ni le résultat d'un outil. Le modèle n'a plus d'outil pour écrire dans la mémoire : c'est My_AI qui le fait, à partir de ce que vous tapez. Une information qu'il ne retient pas de lui-même (« le code de mon casier est le 4815 ») ne reçoit plus « c'est noté », que le modèle ait cherché dans sa mémoire ou répondu d'emblée : la réponse est refaite, et vous rappelle que « retiens ça » la retient.
- **Ne déclenchent rien** : « je retiens que… », « tu te souviens de… ? », une question (« Rappelle-toi : où j'habite ? » demande de s'en souvenir, pas de la retenir), ou une consigne glissée dans une tâche (« écris la fonction, et n'oublie pas que la liste peut être vide »).
- **Sur le téléphone** : les mêmes demandes, avec les indicateurs « 🧠 Mémorisé » et « 🧠 Oublié » au bas de la réponse ; ils y sont encore quand la page est rechargée.
- **Avec des pièces jointes** : ça marche aussi quand le message joint des fichiers (pdf, docx…) ou une image. Un message qui ne fait que demander de retenir suit le chemin habituel, sans faire lire l'image au modèle ; tout autre message part avec l'image et reçoit les faits pour sa réponse.
- **Pas de doublon** : une information déjà connue (casse, accents, ligatures et ponctuation finale ignorés : « sœur » et « soeur » se valent) est rafraîchie au lieu d'être recopiée.
- **Vos mots, pas les siens** : un fait noté à la première personne (« je m'appelle Nicolas ») est présenté au modèle à la troisième personne (« L'utilisateur s'appelle Nicolas »). Il vous répond donc « Tu t'appelles Nicolas », et non « Je m'appelle Nicolas ». L'onglet Faits garde vos mots.
- **Consignes pour l'IA** : ce qui parle d'elle (« retiens que tu t'appelles Jarvis », « retiens que tu dois toujours me répondre en anglais ») est rangé à part, comme une consigne à appliquer dans chaque réponse. Elle prime sur ses réglages par défaut (nom, langue, ton, format), et l'IA en parle à la première personne (« C'est noté : je m'appelle Jarvis »). En anglais aussi : « Remember that your name is Jarvis » → « Noted: my name is Jarvis ». Une question posée en anglais reçoit sa réponse en anglais, même si les faits ont été dictés en français (« What's your name? » → « My name is Jarvis »).
- **Désactiver** : `knowledge_base.auto_extract: false` dans `config.yaml` ; seul l'ajout manuel (➕ Ajouter) reste possible.

---

## 💻 Dans la conversation Code (VS Code, page Code, téléphone)

La conversation Code partage la mémoire de My_AI, cloisonnée : chaque fait a une **portée**, la conversation qui le reçoit d'office.

| Portée | Reçu d'office par | Retenu par |
|---|---|---|
| **Chat** | le chat (fenêtre, téléphone) | le chat, ➕ Ajouter ; tous les faits d'avant les portées |
| **Code : tous les projets** | la conversation Code, quel que soit le dossier ouvert | « retiens pour tous mes projets que… » dans la conversation Code |
| **Code : projet X** | la conversation Code, quand le dossier X est ouvert dans VS Code | « retiens que… », ou une préférence donnée en passant, dans la conversation Code |

- **Retenir** : « Retiens que j'indente avec des tabulations », tapé dans VS Code, sur la page Code ou dans la vue Code du téléphone, est enregistré pour le premier dossier ouvert dans VS Code (« pour ce projet » revient au même). « Retiens pour tous mes projets que… » (ou « … dans tous mes repos », « remember for all my projects that… », « recuerda para todos mis proyectos que… », et de même dans les autres langues) le fait valoir partout ; le même fait retenu avant pour un projet passe alors à tous. Sans dossier ouvert, il vaut pour tous les projets. Une carte « 🧠 Retenu : … » le montre au début de la réponse, sur les trois surfaces, et le modèle le confirme.
- **Le modèle lit ce que vous demandez** : quand votre message demande de retenir, de remplacer ou d'oublier quelque chose, en début de phrase (« retiens… », « souviens-toi… », « garde ça en tête », « oublie que… », « ne retiens plus… », « supprime de ta mémoire… », « remember… », « forget… »), le modèle de la conversation lit quoi, avec les derniers échanges et les faits déjà retenus, en un appel court avant sa réponse, qui le confirme. Pour quels projets, ce sont vos mots qui le disent (« pour tous mes projets », sinon le projet ouvert). « Retiens-le », « retiens ça » retiennent ce qui précède. « Retiens le pour tous mes projets », juste après « retiens que je fais mes tests avec pytest », fait passer ce fait à tous les projets au lieu d'en créer un second. « Retiens que le port est 8000 et ajoute une route /health » retient le port, pas la tâche, qu'il fait ensuite. Un bloc « Retiens ceci : … » (une procédure de déploiement, par exemple) est gardé en entier, avec vos mots. S'il ne sait pas quoi retenir (« retiens-le » en tout début de conversation), rien n'est enregistré, et il vous le demande au lieu de répondre « c'est noté ». Sans Ollama, ou si cet appel échoue, des règles lisent les « retiens que… » comme avant.
- **Oublier, remplacer** : « Oublie que j'utilise unittest » retire ce fait ; « non, retiens plutôt que j'utilise pytest » met le nouveau à la place de l'ancien ; « oublie tout ce que tu as retenu pour ce projet » retire tous ceux du projet, et garde ceux de tous vos projets. Une carte « 🧠 Oublié : … » montre chaque fait retiré, sur les trois surfaces. Comme dans le chat, un second appel court confirme chaque fait à retirer. Ce qui n'est pas dans la mémoire du code n'est pas inventé : rien n'est retiré, et le modèle vous le dit. Si le nouveau fait d'un remplacement ne peut pas être gardé, l'ancien reste.
- **Sans « retiens »** : une préférence durable donnée en passant (« J'utilise toujours black pour formater mon code », « dans ce projet, les noms de variables sont en anglais ») est retenue d'elle-même, et une carte « 🧠 Retenu » la montre à la fin de la réponse. Le modèle lit votre message pendant qu'il vous répond : la réponse n'attend pas. Il ne retient ni la tâche demandée, ni une question, ni un détail du travail en cours, et dans le doute, rien. Une préférence qui contredit un fait déjà retenu (« maintenant je formate mon code avec ruff », après « j'utilise toujours black ») le remplace ; sans demande, il ne retire rien d'autre. Un message de moins de trois mots (« ok merci ») n'est pas lu.
- **Seul votre message compte** : un fichier du workspace ou un résultat d'outil ne peut rien écrire dans la mémoire, et le modèle n'a pas d'outil pour le faire. Ce qu'il retient doit venir de ce que vous avez écrit (au moins la moitié de ses mots qui comptent), sinon il n'est pas retenu : une phrase glissée dans le README d'un dépôt cloné deviendrait sinon une consigne permanente. Une question introduite par « rappelle-toi » (« Rappelle-toi : quel framework j'utilise ? ») demande de s'en souvenir, pas de retenir.
- **Ce que le modèle reçoit d'office** : les faits du code (tous les projets, et ceux des dossiers ouverts), dans son prompt système, avec la consigne de les appliquer sans les recopier dans les fichiers. Les faits du chat (vous, vos proches, vos consignes de ton) n'y vont pas : avec eux sous les yeux, le modèle les glissait dans le code. Ce prompt n'est refait que si la mémoire change ailleurs (un fait modifié ou supprimé dans le panneau) ou si le dossier, la langue ou le jour changent : un « retiens que… » de la conversation ne le refait pas, et Ollama n'a pas à relire toute la conversation.
- **Le reste, à la demande** : l'outil `search_memory`, exécuté sur le PC et jamais par l'extension, cherche dans les faits du chat, du code et des dossiers ouverts (pas ceux des autres projets), puis dans les documents du panneau (cahier des charges, notes…). Le modèle ne s'en sert que si vous parlez de votre mémoire ou d'un document que vous y avez mis ; faute de fait qui corresponde, il ne reçoit que ceux du code. Sa carte « Recherche de « … » dans la mémoire » s'affiche aussi sur les trois surfaces.
- **Dans le panneau Mémoire** : un fait du code porte sa portée en tête de sa provenance (« 💻 Code : projet My_AI », « 💻 Code : tous les projets »), source `code`. Il se modifie et se supprime comme les autres ; le chat le trouve à la demande (`search_memory`), avec sa portée, par ses mots, par le nom de son projet ou par le mot « code » : une recherche « règles de code My_AI » ramène ceux de My_AI d'abord, puis ceux de tous les projets. Pour que le chat cherche dans sa mémoire, parlez-lui de ce que vous lui avez demandé de retenir (« qu'est-ce que je t'ai demandé de retenir pour mes projets de code ? ») : à « quelles règles de code pour My_AI ? », il cherche plutôt un fichier sur le disque.
- **Désactiver** : `knowledge_base.auto_extract: false` arrête aussi tout ce que la conversation Code retient, remplace ou oublie, demandé ou non.

---

## 📄 Documents

L'onglet **Documents** garde le texte des documents. Pour la recherche, chaque document est découpé en interne en morceaux de 256 tokens (chunks), que l'onglet ne montre pas : il montre des documents.

- **Joints dans le chat** : chaque fichier joint (PDF, Word, Excel, PowerPoint, code…) y entre de lui-même, dès qu'il est lu, sans rien demander. Une image jointe y entre aussi, une fois son message envoyé et sa réponse finie (sur le PC comme depuis le téléphone) : le modèle de vision sert d'abord la réponse, puis décrit l'image pour la mémoire. Une pièce jointe retirée avant l'envoi n'y reste pas.
- **Ajoutés à la main** : bouton **➕ Ajouter** de l'onglet (dialogue de fichiers, plusieurs à la fois), ou fichiers **glissés sur le panneau**, d'où qu'ils viennent (Explorateur, pièce jointe d'Outlook, archive ZIP ouverte…) : pendant le survol, sur l'onglet Documents, le contour du panneau Mémoire s'éclaire en orange, et le contenu des fichiers déposés est lu même s'ils n'ont pas de chemin sur le disque. Formats : ceux des pièces jointes (PDF, Word, Excel et CSV, PowerPoint, code et texte, images). Les fichiers sont lus en arrière-plan, un à la fois, et s'affichent en tête de liste pendant leur lecture (« en attente », « lecture du fichier… », « description de l'image… ») ; une notification donne le résultat de chacun. Un format non pris en charge est refusé. Leur ligne porte « ajouté à la main ».
- **Dossiers déposés** : un dossier glissé sur le panneau (onglet Documents) y entre avec tous ses fichiers lisibles, sous-dossiers compris, rangés sous le nom du dossier : l'onglet le montre comme un dossier à déplier. Comme pour les dossiers du projet, les fichiers et dossiers cachés et les dossiers de dépendances ou de build (`.git`, `node_modules`, `venv`, `dist`…) sont laissés de côté, ainsi que les formats non pris en charge et les fichiers trop lourds (plus de 2 Mo pour un texte ou du code, 50 Mo pour le reste) ; une notification dit combien. Au plus 200 fichiers par dossier : au-delà, rien n'est envoyé, déposez plutôt ses sous-dossiers. Pendant la lecture, la file de l'onglet montre le dossier sur une seule ligne (fichiers restants, fichier en cours), et un seul bilan s'affiche à la fin (« 📁 « site » : 2 fichiers ajoutés, 1 mis à jour, 3 déjà à jour. »).
- **Images** (ajoutées ou jointes au chat) : le modèle de vision les décrit (le modèle de chat, comme dans le chat ; 30 s à 1 min par image sur le PC de développement, GPU intégré), puis l'OCR lit leur texte visible ; les deux sont rangés, sous les titres « Description de l'image » et « Texte lu dans l'image ». L'un ou l'autre suffit : une photo sans texte reste retrouvable par sa description, une capture d'écran par son texte, même sans Ollama. Une image est reconnue à son contenu, pas à son nom : la même image, rejointe ou ajoutée de nouveau (même sous un autre nom), n'est ni décrite ni rangée une seconde fois. Leur provenance porte 🖼️. Une image du chat avance dans la file de l'onglet sans notification, comme les documents joints.

Un document ajouté à la main est lu par les mêmes lecteurs qu'une pièce jointe du chat : le même fichier, joint ensuite, n'est pas rangé une seconde fois.

**Affichage** : une ligne par document, avec sa date et « ajouté à la main » le cas échéant ; un document ne se déplie pas. Un dossier déposé tient sur une ligne (nombre de fichiers, date) et se déplie sur ses fichiers, rangés par chemin. Du plus récent au plus ancien : un document ajouté apparaît en tête de la première page. La recherche garde les documents dont le nom ou le texte la contient. L'en-tête du panneau compte des documents (un fichier d'un dossier en est un).

**Deux fichiers du même nom** restent deux documents : c'est à vous de vous organiser, leur date d'ajout les distingue. « rapport.pdf » ajouté seul et « projet/rapport.pdf » venu d'un dossier déposé sont toujours deux documents différents ; deux dossiers déposés du même nom aussi.

**Remettre un fichier ou un dossier sous un nom déjà pris** (par « Ajouter » ou par un dépôt) : une fenêtre le signale, avec la date de celui qui est déjà là (le plus récent, s'il y en a plusieurs), une seule fois pour tout ce qui est remis ensemble.

- **Mettre à jour** : il remplace celui-là (« 🔄 mis à jour ») ; même contenu, rien ne change (« à l'identique »). Un dossier garde ses fichiers inchangés sans les relire (une image n'est pas redécrite), remplace les modifiés, ajoute les nouveaux et retire ceux qu'il ne contient plus.
- **Garder les deux** : il s'ajoute à côté. Un fichier au contenu identique n'est pas recopié.
- **Annuler** (ou Échap) : il n'est pas envoyé ; les nouveaux, remis en même temps, sont ajoutés.

Un fichier joint au chat ne pose pas de question : même contenu, c'est le même document ; contenu différent, il s'ajoute à côté (« joint au chat »).

**Retirer une pièce jointe** avant l'envoi l'efface de l'onglet, sauf si le document y était déjà avant elle (joint dans une conversation précédente, ou ajouté à la main) : il y reste.

**Dans une réponse**, un document ou un dossier de l'onglet que le modèle cite (« `Data.xlsx` », « projet/rapport.pdf », le dossier « OneDrive_3_06-10-2026 ») est un lien, même collé à du japonais, du chinois ou du coréen (« Data.xlsxには ») : un clic ouvre l'onglet Documents, cherché sur son nom, son dossier déplié ; pour un fichier d'un dossier, c'est tout le dossier qui s'ouvre, déplié, ce fichier en évidence. Un lien Markdown que le modèle invente vers l'un d'eux (« [Dossier OneDrive_3_06-10-2026](memory://one drive) ») aussi ; un lien vers un chemin du disque qui existe montre ce fichier dans l'Explorateur. Un nom courant (un dossier « projet ») n'est un lien qu'écrit en `code` ou dans un lien, pas au fil du texte.

---

## 📨 Ce que le modèle reçoit

| Onglet | Envoyé au modèle |
|---|---|
| **Faits** | Ceux du chat, automatiquement, dans le prompt système de chaque réponse, y compris avec un fichier ou une image joints : d'abord les faits qui partagent des mots avec votre message (casse, accents, ligatures et pluriels ignorés), puis les plus récents, jusqu'à 12 faits ou 2 500 caractères. Ils restent dans la réponse rédigée après un appel d'outil. Ceux du code vont à la conversation Code (voir [Dans la conversation Code](#-dans-la-conversation-code-vs-code-page-code-téléphone)) ; le chat les trouve à la demande avec `search_memory`, par leurs mots, le nom de leur projet ou le mot « code ». |
| **Documents** | Ceux que votre message nomme (« rapport.pdf », « projet/rapport.pdf », ou un nom distinctif sans extension : « le rapport trimestriel ») : leur contenu utile, dans le prompt système, chacun sous son nom, son dossier éventuel et sa date d'ajout. Plusieurs du même nom : tous, numérotés, avec un avertissement (ce sont des fichiers différents) et, après leur contenu, un rappel : répondre pour chacun, l'un après l'autre, sauf si la question dit lequel ; nommer aussi le dossier ne garde que le sien. Un fichier joint à la conversation passe avant celui de la mémoire qui porte son nom. Un dossier déposé que le message désigne (« le dossier projet », ou un mot de son nom autour de « dossier » si le message parle de la mémoire : « mon dossier onedrive que tu as en mémoire » pour « OneDrive_3_06-10-2026 ») : la liste de ses fichiers, ses extraits les plus proches de la question, et le rappel qu'il est dans la mémoire, pas sur le disque ; si le modèle essaie quand même de lire l'un de ses fichiers sur le disque (`read_local_file("OneDrive_3_06-10-2026/Data.xlsx")`), l'outil le lit dans la mémoire. Sans parler de la mémoire (« il y a quoi dans mon dossier onedrive ? »), c'est peut-être un dossier du disque : le modèle reçoit seulement un rappel de ce dossier de la mémoire au nom proche, pour ne pas les confondre ; et si sa réponse ne le cite pas, la fenêtre le signale sous elle (« Aussi dans la Mémoire : 📁 OneDrive_3_06-10-2026 (2 fichiers) », cliquable). « Dossier » et « mémoire » sont reconnus dans les 12 langues de l'application (folder et memory, Ordner et Gedächtnis, carpeta et memoria, フォルダ et 記憶…), et un nom de fichier collé au japonais, au chinois ou au coréen (« Data.xlsxの中身 ») compte. Sinon, quand le modèle appelle l'outil `search_memory` (qui cherche aussi dans les faits) : chaque extrait y indique son document, et l'outil peut se limiter à un document ou à un dossier. |
| **Conversations** | Jamais : c'est l'index de la recherche globale de la barre latérale. |

**Fichiers et documents générés** (« génère un fichier… », Word, PDF, PowerPoint, Excel) : leur contenu est rédigé à part, et il reçoit les faits **sur vous** seulement quand la demande parle de vous. C'est le cas avec « mon prénom », « mon entreprise », « mon équipe », « mon chat »…, ou pour un CV, une lettre ou une carte de visite. « Génère un fichier qui affiche mon prénom » écrit donc votre prénom, alors qu'un script de tri ou un rapport sur les baleines restent neutres : avec les faits sous les yeux, le modèle les glissait partout. Les consignes pour l'IA (« termine tes réponses par… ») ne s'appliquent qu'au chat.

---

## ✨ Ce que vous pouvez faire

### ➕ Ajouter
- **Faits** : bouton **➕ Ajouter**, catégorie et contenu (source « manual »).
- **Documents** : bouton **➕ Ajouter**, ou dépôt de fichiers ou de dossiers sur le panneau, onglet Documents ouvert (voir [Documents](#-documents)).

### 👁️ Voir
- **3 onglets** : Faits · Documents · Conversations.
- **Recherche** dans l'onglet courant + **filtre par catégorie** (onglet Faits).
- **Pagination** (20 entrées/page).
- **Provenance** affichée sous chaque entrée :
  - Faits → portée d'un fait du code (« 💻 Code : projet My_AI », « 💻 Code : tous les projets »), `source` (manuel / conversation / code / …), `confiance`, date de mise à jour.
  - Conversations → **session** (son nom actuel : renommer une conversation change aussi celui-ci) · rôle (vous / assistant) · horodatage.
  - Documents → une ligne par **document** (date · « ajouté à la main » le cas échéant) ou par **dossier déposé** (fichiers · date), à déplier sur ses fichiers. Une recherche qui ne trouve qu'une partie des fichiers d'un dossier n'affiche qu'eux, et le dit : « 1 fichier sur 4 » (videz la recherche pour voir tout le dossier).

### ✏️ Éditer
- Bouton **✏️** (faits et conversations) : édition **inline** du contenu, puis **💾 Enregistrer** / **✖ Annuler**. Un document se met à jour en le remettant (voir [Documents](#-documents)).
- Pour un **document/conversation**, le texte est **ré-encodé** (nouvel embedding) afin que la recherche reste cohérente.

### 🗑️ Supprimer
- Bouton **🗑️** → **dialogue de confirmation** (cohérent avec la confirmation MCP existante).
- Onglet Documents : le 🗑️ d'un **document** le supprime en entier ; celui d'un **dossier déposé**, avec tous ses fichiers ; celui d'un fichier du dossier déplié, ce fichier seul.
- La suppression d'une **entrée vectorielle** est une **vraie suppression dans ChromaDB** (`collection.delete`).

#### Cas particulier : les conversations (« supprimer à la source »)
L'onglet **Conversations** affiche un **index** reconstruit depuis vos workspaces. Une suppression directe dans l'index **réapparaîtrait** au prochain réindex. C'est pourquoi le dialogue propose une case :

> ☑ **Supprimer aussi le message d'origine** *(sinon réapparaît au prochain réindex)*

- **Cochée (défaut)** → le **message d'origine** est retiré du workspace, puis l'index est **reconstruit** : la suppression est **durable**.
- **Décochée** → suppression **transitoire** de l'index uniquement (réapparaît au prochain réindex forcé).

L'édition d'une entrée de conversation propage de même la modification au **message d'origine**.

---

## 🏗️ Sous le capot

```
frontend/src/features/panels/memory/   # Panneau « Mémoire » de la fenêtre ; folders.ts :
                                      # dossier déposé parcouru dans la page
interfaces/desktop/memory.py          # Service du panneau (routes : api_memory.py) ;
        │  appelle                     # message d'origine modifié via le ChatService ;
        │                              # documents ajoutés, dossiers déposés (un bilan
        │                              # par dossier) et images envoyées dans le chat
        │                              # (on_images_sent) lus en arrière-plan
        ├─ core/document_memory.py     # Lecture d'un fichier ajouté (lecteurs du chat,
        │                              # image : description par la vision + OCR)
        ▼
core/memory_store.py  ── MemoryStore  # Façade CRUD unifiée (testable sans interface)
        │                  exposé par AIEngine.get_memory_store()
        ├─ core/knowledge_base_manager.py   # Faits (SQLite) — CRUD, portée de chaque fait
        └─ memory/vector_memory.py          # Vecteurs (ChromaDB) — CRUD par entrée
             ├─ list_entries / get_entry / count_entries
             ├─ update_entry  (ré-embarque)
             ├─ delete_entry  (vraie suppression ChromaDB)
             └─ memory/embedding_reindex.py  # Changement de modèle : copie en arrière-plan

core/embedding_engine.py           # Modèle d'embeddings (Granite, repli MiniLM) :
                                   # encode / encode_query / encode_document,
                                   # nom de collection par modèle

core/ai_engine.py                  # Côté chat
   ├─ _remember_from_message()     # « retiens… », « oublie… » : fait avant la réponse
   ├─ _read_memory_later()         # sans demande : lu pendant la réponse, signalé à la fin
   ├─ outil search_memory          # search_memory() : partagé avec la conversation Code
   └─ _knowledge_base_context()    # select_facts() (faits du chat) → prompt système

core/chat_memory.py                # Ce qu'un message du chat change (ChatMemory) : le
                                   #   modèle du chat lit quoi (ChatMemoryReader)

core/code_memory.py                # Côté conversation Code (relay/code_hub.py) : faits du code
   ├─ prompt_block()               #   → section « Mémoire » du prompt système
   ├─ update()                     # ce qu'un message change : le modèle lit quoi retenir,
   │                               #   remplacer ou oublier (MemoryReader) ; demandé : avant
   │                               #   la réponse ; sinon : pendant, une préférence durable
   └─ search()                     # outil search_memory, exécuté sur le PC
```

### `MemoryStore` (API principale, pour développeurs)

```python
store = ai_engine.get_memory_store()

# Faits
items, total = store.list_facts(query="", category=None, limit=25, offset=0)
store.add_fact(category, key, value, source="manual")
store.update_fact(fact_id, value)
store.delete_fact(fact_id)

# Vecteurs (collection_type = "document" | "conversation")
items, total = store.list_vectors("document", query="", limit=25, offset=0)
store.add_document(content, name, {"source": "manual", "type": "PDF"})  # « added » | « duplicate », document_id
store.update_vector(entry_id, new_text, "document", at_source=True, metadata=None)
store.delete_vector(entry_id, "conversation", at_source=True, metadata=None)

# Onglet Documents : documents et dossiers déposés (métadonnées « folder », « folder_id »)
groups, total = store.list_document_groups(query="", limit=20, offset=0)
index = store.document_index()       # un enregistrement par document (nom, dossier, date…)
text = store.document_text(document_id)  # texte recomposé de ses morceaux
store.delete_document(document_id)   # tous ses morceaux (« Mettre à jour » : la cible)
store.delete_folder(folder_key)      # tous ses fichiers ; un autre dossier du même nom reste
store.remove_other_versions("site/src/app.py", nouvel_id, folder_id=…)  # ancienne version
store.prune_folder(folder_key, noms_du_depot)  # dossier mis à jour : fichiers disparus retirés

# Pour le modèle (core/memory_documents.py) : libellés, documents nommés, extraits groupés
memory_documents_block(question, store, budget, passages)   # contexte de la réponse
results_block(resultats)                                     # extraits de search_memory

# Vue d'ensemble & provenance
store.stats()                       # {"facts": n, "documents": n, "conversations": n}
MemoryStore.describe_provenance(item)
```

Pour les conversations, `at_source=True` modifie le message d'origine du workspace puis déclenche un réindex incrémental (suppression/édition **durable**). `at_source=False` n'agit que sur l'index ChromaDB.

---

## ❓ FAQ

**Si je dis « retiens ceci » dans le chat, est-ce vraiment retenu ?**
Oui : le fait apparaît dans l'onglet **Faits** et sert dans les conversations suivantes (voir [Mémoriser depuis le chat](#-mémoriser-depuis-le-chat)). Vous pouvez le modifier ou le supprimer comme n'importe quel fait.

**Les fichiers joints dans le chat sont-ils gardés ?**
Oui : ils entrent d'eux-mêmes dans l'onglet **Documents**, et l'outil `search_memory` les retrouve dans les conversations suivantes. Une image y entre décrite et lue, une fois la réponse à son message finie (voir [Documents](#-documents)). Supprimez-les dans l'onglet pour qu'ils soient oubliés.

**Que se passe-t-il si je remets un fichier dont le nom est déjà en mémoire ?**
Une fenêtre le signale, avec la date de celui qui est déjà là, et propose de le mettre à jour, de garder les deux, ou d'annuler. Pour un dossier, la mise à jour remplace les fichiers modifiés, ajoute les nouveaux et retire ceux qu'il ne contient plus (voir [Documents](#-documents)).

**Et si je joins au chat un fichier qui porte le nom d'un document de la mémoire ?**
Aucune question : de même contenu, c'est le même document ; de contenu différent, il s'ajoute à côté (« joint au chat », avec sa date), sans rien remplacer. Dans cette conversation, le modèle lit le fichier joint. Plus tard, une question sur ce nom lui donne les deux, chacun sous son origine et sa date, avec la consigne de ne pas les confondre.

**Avec deux fichiers du même nom, le modèle se trompe-t-il de fichier ?**
Il reçoit chacun sous son libellé : nom ou chemin dans son dossier, « ajouté à la main », « joint au chat » ou « fichier du dossier … », et sa date. Nommer le dossier (« le rapport.pdf du dossier projet ») ne lui donne que celui-là ; dire « celui que j'ai ajouté à la main » ou sa date suffit aussi. Sinon (« Résume rapport.pdf »), il répond pour chacun, l'un après l'autre, sous un titre qui dit lequel c'est. Dans une conversation où un « rapport.pdf » est joint, c'est de lui qu'on parle, sauf si le message nomme un dossier.

**Peut-on mettre un dossier entier en mémoire ?**
Oui : glissez-le sur le panneau Mémoire, onglet Documents ouvert. Ses fichiers lisibles y entrent, rangés sous le nom du dossier, jusqu'à 200 fichiers (voir [Documents](#-documents)). Le 🗑️ du dossier le supprime en entier, celui d'un de ses fichiers ce fichier seul.

**La suppression efface-t-elle vraiment les données ?**
Oui. Les faits sont supprimés de la base SQLite ; les entrées vectorielles via `ChromaDB.delete`. Pour les conversations, l'option « à la source » retire aussi le message du workspace.

**Le chiffrement est-il géré ?**
Oui. Si le chiffrement AES-256 de la mémoire vectorielle est actif, les entrées sont **déchiffrées** pour l'affichage et **re-chiffrées** à l'édition. La réindexation après un changement de modèle déchiffre le texte pour le calcul seulement : il reste chiffré dans la base.

**Après la mise à jour, la recherche ne trouve pas tout ?**
La mémoire est recalculée avec le nouveau modèle, en arrière-plan, juste après le lancement (« 🔄 Réindexation de la mémoire » dans la console, puis « ✅ Réindexation terminée »). Les entrées apparaissent au fur et à mesure ; rien n'est perdu (voir [Recherche multilingue](#-recherche-multilingue)).

**Est-ce que ça reste local ?**
Entièrement. Toutes les opérations s'effectuent sur les fichiers locaux (`data/knowledge_base/`, `memory/vector_store/`).

---

> Voir aussi : [CONVERSATION_SEARCH.md](CONVERSATION_SEARCH.md) (recherche globale), [ULTRA_10M_TOKENS.md](ULTRA_10M_TOKENS.md) (mémoire vectorielle), [CHANGELOG.md](CHANGELOG.md).
