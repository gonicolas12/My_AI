"""
Demandes de génération d'image dans les autres langues de l'interface.

Le français garde ses expressions dans AIEngine (_IMAGE_GEN_RE). Ici, une
expression par langue, pour qu'un « generate an image of a cat » ou un
« 猫の画像を生成して » produisent une image comme « génère une image de chat ».

Comme en français, il faut un verbe de création suivi d'un nom d'image (ou un
« dessine-moi ») : « create an image resizer » reste une demande de code, et
« draw me a diagram » un schéma pour le modèle.
"""

import re
from typing import List, Tuple

# Mots qui peuvent précéder le nom (« a realistic photo of ») : deux au plus,
# jamais un déterminant (« make the image bigger » retouche, ne crée pas)
_ADJ_EN = r"(?:(?!(?:the|this|that|these|those|my|your|its|our|their)\b)[\w'-]+\s+){0,2}?"
_ADJ_ES = r"(?:(?!(?:el|la|los|las|esta|este|esa|ese|mi|tu|su)\b)[\w-]+\s+){0,2}?"
_ADJ_DE = (r"(?:(?!(?:das|der|die|dem|den|dieses|diese|dieser|mein|meine|dein|deine|sein|seine)\b)"
           r"[\w-]+\s+){0,2}?")
_ADJ_IT = (r"(?:(?!(?:il|lo|la|i|gli|le|questa|questo|quella|quello|mio|mia|tuo|tua)\b)"
           r"[\w-]+\s+){0,2}?")
_ADJ_PT = r"(?:(?!(?:o|a|os|as|esta|este|essa|esse|meu|minha|seu|sua)\b)[\w-]+\s+){0,2}?"
_ADJ_NL = r"(?:(?!(?:de|het|deze|dit|die|dat|mijn|jouw|zijn|haar)\b)[\w'-]+\s+){0,2}?"
_ADJ_RU = r"(?:(?!(?:это|эту|этот|эти|мою|мой|твою|твой)\b)[\w-]+\s+){0,2}?"

# Après le nom : ce qui annonce le sujet de l'image, ou la fin de la demande
_TAIL_EN = r"(?=\s+(?:of|showing|depicting|featuring|with|for|in the style)\b|\s*[:,.!?]|\s*$)"
_TAIL_ES = r"(?=\s+(?:de|del|que|con|sobre|mostrando|para|al estilo)\b|\s*[:,.!?]|\s*$)"
_TAIL_DE = (r"(?=\s+(?:von|vom|mit|über|ueber|zum|zur|für|fuer|im stil|ein(?:e[nrs]?)?)\b"
            r"|\s*[:,.!?]|\s*$)")
_TAIL_IT = (r"(?=\s+(?:di|del|della|dello|dei|delle|degli|che|con|su|per|in stile|raffigurante)\b"
            r"|\s*[:,.!?]|\s*$)")
_TAIL_PT = (r"(?=\s+(?:de|do|da|dos|das|com|que|mostrando|sobre|para|no estilo|representando)\b"
            r"|\s*[:,.!?]|\s*$)")
_TAIL_NL = r"(?=\s+(?:van|met|over|die|dat|voor|in de stijl)\b|\s*[:,.!?]|\s*$)"

# (langue, demande) ; le groupe « subject » garde le sujet pris dans la demande
_REQUESTS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("en", re.compile(
        r"\b(?:generate|create|make|draw|paint|render|produce|design)\s+(?:me\s+)?"
        r"(?:an?\s+|some\s+)?" + _ADJ_EN
        + r"(?:images?|pictures?|illustrations?|drawings?|photos?|paintings?|portraits?|logo|"
        r"poster|artwork|sketch|wallpaper)" + _TAIL_EN
        + r"|\b(?:draw|paint|sketch)\s+me\b",
        re.IGNORECASE)),
    ("es", re.compile(
        r"\b(?:genera|genérame|generame|generar|crea|créame|creame|crear|haz|hazme|hacer|dibuja|"
        r"dibújame|dibujame|dibujar|pinta|píntame|pintame|ilustra|diseña|diséñame|diseñame|diseñar)"
        r"\s+(?:me\s+)?(?:una?\s+|unas\s+|unos\s+)?" + _ADJ_ES
        + r"(?:imagen|imágenes|imagenes|ilustración|ilustracion|ilustraciones|dibujos?|fotos?|"
        r"fotografía|fotografia|pintura|retrato|logo|logotipo|póster|poster|cartel|boceto)"
        + _TAIL_ES
        + r"|\b(?:dibújame|dibujame|píntame|pintame)\b",
        re.IGNORECASE)),
    ("de", re.compile(
        r"\b(?:generiere|generier|erstelle|erstell|erzeuge|erzeug|mache|mach|zeichne|male|gestalte|"
        r"entwirf|entwerfe)\s+(?:mir\s+|uns\s+)?(?:ein(?:e[nr]?)?\s+|einige\s+)?" + _ADJ_DE
        + r"(?:bild|bilder|illustration|illustrationen|zeichnung|zeichnungen|foto|fotos|gemälde|"
        r"gemaelde|porträt|portrait|logo|poster|plakat|skizze)" + _TAIL_DE
        + r"|\b(?:zeichne|male)\s+mir\b"
        # Verbe à la fin : « kannst du mir ein Bild von einer Katze erstellen? »
        r"|\bein(?:e[nr]?)?\s+(?:[\w-]+\s+)?(?:bild|illustration|zeichnung|foto|gemälde|logo|"
        r"poster|plakat|skizze)\b[^.!?\n]{0,80}?\b(?:generieren|erstellen|erzeugen|zeichnen|malen|"
        r"machen|gestalten|entwerfen)\b",
        re.IGNORECASE)),
    ("it", re.compile(
        r"\b(?:genera|generami|generare|crea|creami|creare|fai|fammi|fare|disegna|disegnami|"
        r"disegnare|dipingi|dipingimi|dipingere|illustra|realizza|realizzami|realizzare)"
        r"\s+(?:mi\s+)?(?:un['’]|una\s+|un\s+|uno\s+|delle\s+|degli\s+|dei\s+)?" + _ADJ_IT
        + r"(?:immagine|immagini|illustrazione|illustrazioni|disegno|disegni|foto|fotografia|"
        r"dipinto|ritratto|logo|poster|manifesto|locandina|schizzo)" + _TAIL_IT
        + r"|\b(?:disegnami|dipingimi)\b",
        re.IGNORECASE)),
    ("pt", re.compile(
        r"\b(?:gere-me|gere|gera|gerar|crie-me|crie|cria|criar|faça-me|faça|faca|faz|fazer|"
        r"desenhe-me|desenhe|desenha|desenhar|pinte|pinta|pintar|ilustre|ilustra|elabore)"
        r"\s+(?:me\s+|pra mim\s+|para mim\s+)?(?:uma?\s+|umas\s+|uns\s+)?" + _ADJ_PT
        + r"(?:imagem|imagens|ilustração|ilustracao|ilustrações|ilustracoes|desenhos?|fotos?|"
        r"fotografia|pintura|retrato|logo|logotipo|pôster|poster|cartaz|esboço|esboco)" + _TAIL_PT
        + r"|\b(?:me\s+desenhe|me\s+desenha|desenha-me)\b",
        re.IGNORECASE)),
    ("nl", re.compile(
        r"\b(?:genereer|maak|creëer|creeer|teken|schilder|ontwerp)\s+(?:voor\s+mij\s+|voor\s+me\s+|"
        r"me\s+|mij\s+)?(?:een\s+|enkele\s+|wat\s+)?" + _ADJ_NL
        + r"(?:afbeelding|afbeeldingen|plaatje|plaatjes|illustratie|illustraties|tekening|"
        r"tekeningen|foto|foto's|schilderij|portret|logo|poster|schets)" + _TAIL_NL
        + r"|\b(?:teken|schilder)\s+(?:voor\s+)?(?:me|mij)\b"
        # Verbe à la fin : « kun je een afbeelding van een kat maken? »
        r"|\been\s+(?:[\w-]+\s+)?(?:afbeelding|plaatje|illustratie|tekening|foto|schilderij|logo|"
        r"poster)\b[^.!?\n]{0,80}?\b(?:genereren|maken|creëren|creeren|tekenen|schilderen|"
        r"ontwerpen)\b",
        re.IGNORECASE)),
    ("ru", re.compile(
        r"\b(?:сгенерируй|сгенерируйте|сгенерировать|создай|создайте|создать|сделай|сделайте|"
        r"сделать|нарисуй|нарисуйте|нарисовать|изобрази|изобразите|изобразить)"
        r"\s+(?:мне\s+|нам\s+)?"
        + _ADJ_RU
        + r"(?:изображение|изображения|картинку|картинки|картину|иллюстрацию|иллюстрации|рисунок|"
        r"рисунки|фото|фотографию|фотку|портрет|логотип|постер|плакат|эскиз|арт)\b"
        r"|\b(?:нарисуй|нарисуйте|изобрази|изобразите)\b",
        re.IGNORECASE)),
    ("zh", re.compile(
        r"(?:生成|创作|绘制|制作|设计|画|做)(?:一下)?(?:一?[张幅个份些])?(?P<subject>[^，。！？,.!?\n]{0,12}?)"
        r"(?:图片|图像|插图|插画|照片|肖像|海报|画作|壁纸|头像|标志|logo|图标)"
        r"(?!压缩|处理|识别|上传|下载|编辑|转换|格式|查看|浏览|分类|管理|工具|程序|网站|代码|脚本|库|功能|接口)"
        r"|画(?:一?[只个张幅头条匹棵朵座位]|出)"
        r"|文生图",
        re.IGNORECASE)),
    ("ja", re.compile(
        r"(?:画像|イラスト|絵|写真|ポスター|ロゴ|肖像画|壁紙|アイコン)(?:を|も)?\s*"
        r"(?:生成|作成|作って|作る|つくって|描いて|描く|描け|かいて)"
        r"|を\s*(?:描いて|描け|かいて)",
        re.IGNORECASE)),
    ("ko", re.compile(
        r"(?:이미지|그림|사진|일러스트|포스터|로고|초상화|배경화면|아이콘)(?:을|를|도)?\s*"
        r"(?:생성|만들어|만들|그려|그리|제작)"
        r"|그려\s*(?:줘|주세요|줄래|주실)",
        re.IGNORECASE)),
    ("ar", re.compile(
        r"(?:أنشئ|انشئ|أنشىء|ولّد|اصنع|اعمل|صمّم|صمم|ارسم|توليد|إنشاء|انشاء)\s+(?:لي\s+)?"
        r"(?:\S+\s+){0,2}?"
        r"(?:صورة|صورا|صوراً|صور|رسمة|رسما|رسماً|لوحة|شعار|ملصق|ملصقا|بوستر|أيقونة)"
        r"|\b(?:ارسم|ارسمي)\s+لي\b",
        re.IGNORECASE)),
]

# Demandes d'ANALYSE d'une image jointe, schémas ou graphiques (le modèle les
# écrit mieux qu'un générateur ne les dessine) et images de conteneur ou de disque
_EXCLUDE = re.compile(
    r"\b(?:describe|analy[sz]e|identify|recogni[sz]e|caption|what(?:'s| is) in)\b"
    r"|\b(?:this|that|the attached) (?:image|picture|photo)\b"
    r"|\b(?:chart|graph|diagram|flowchart|plot)s?\b"
    r"|\b(?:descríbeme|describeme|analiza|identifica|reconoce)\b|qué (?:hay|ves) en"
    r"|\b(?:esta|esa) (?:imagen|foto|fotografía)\b|imagen adjunta|\b(?:gráfico|diagrama)s?\b"
    r"|\b(?:beschreibe|beschreib|analysiere|analysier|erkenne|identifiziere)\b"
    r"|was (?:ist|siehst du) auf"
    r"|\b(?:dieses|diesem|das angehängte) (?:bild|foto)\b|\b(?:diagramm|schaubild|flussdiagramm)\b"
    r"|\b(?:descrivi|analizza|riconosci)\b|cosa (?:c['’]è|vedi)"
    r"|\b(?:questa|quest['’])\s*(?:immagine|foto)\b|immagine allegata|\b(?:grafico|diagramma)\b"
    r"|\b(?:descreva|descreve|analise|analisa|identifique|reconheça)\b|o que (?:há|tem) n"
    r"|\b(?:esta|essa) (?:imagem|foto)\b|imagem anexada"
    r"|\b(?:beschrijf|analyseer|herken|identificeer)\b|wat (?:staat er|zie je)"
    r"|\b(?:deze|die) (?:afbeelding|foto)\b|\b(?:grafiek|stroomdiagram)\b"
    r"|\b(?:опиши|опишите|проанализируй|проанализируйте|распознай)\b|что (?:на|изображено)"
    r"|\b(?:этой|эту|этом|это) (?:изображени\w*|картинк\w*|фото\w*)\b|график|диаграмм|схем|таблиц"
    r"|这张图|这个图|这幅图|图片中|图片里|图中|描述|分析|识别"
    r"|流程图|柱状图|饼图|折线图|图表|思维导图|架构图|示意图|表格"
    r"|この画像|この写真|この絵|画像に|写真に|説明して|分析|何が写|読み取|グラフ|チャート|図表"
    r"|フロー図|構成図|概念図|模式図|回路図|ER図|UML"
    r"|(?<!\S)이 (?:이미지|사진|그림)|이미지에서|사진에서|설명해|분석|무엇이|뭐가|그래프|차트|도표|다이어그램|순서도"
    r"|هذه الصورة|الصورة المرفقة|\bصف\b|\bحلل\b|ماذا (?:يوجد|في)|بياني|بيانية|مخطط|جدول"
    r"|docker|podman|kubernetes|\bcontainers?\b|contenedor|contenitore|contêiner|conteiner"
    r"|контейнер|容器|コンテナ|컨테이너|حاوية|\biso\b|\bqcow2?\b|\bvmdk\b",
    re.IGNORECASE,
)

# Avant le sujet de l'image : mots de liaison et articles
_LEAD = re.compile(
    r"^[\s:,.-]*(?:(?:of|showing|depicting|featuring|with|for|the|an?|de|del|que|con|sobre|"
    r"mostrando|el|una?|unos|unas|von|vom|mit|über|ein(?:e[nrs]?)?|di|della|dello|che|"
    r"raffigurante|il|lo|la|le|un['’]|uno|do|da|dos|das|com|representando|o|um|uma|van|met|"
    r"een)\b[\s:,.-]*)*",
    re.IGNORECASE,
)
# Langues où le sujet précède la demande (« 猫の画像を生成して »)
_SUBJECT_FIRST = {"ja", "ko"}
_TRAILING_PARTICLES = re.compile(r"(?:\s*(?:の|を|も|을|를|의|도))+\s*$")


def is_image_request(text: str) -> bool:
    """True si ``text`` demande de créer une image, dans l'une des langues ci-dessus."""
    if not text or _EXCLUDE.search(text):
        return False
    return any(pattern.search(text) for _, pattern in _REQUESTS)


def strip_image_request(text: str) -> str:
    """Sujet de l'image, sans la demande (« generate an image of a cat » → « cat »).

    Best-effort : chaîne vide si aucune demande n'est reconnue ou s'il ne reste rien.
    """
    for language, pattern in _REQUESTS:
        match = pattern.search(text or "")
        if not match:
            continue
        if language in _SUBJECT_FIRST:
            subject = _TRAILING_PARTICLES.sub("", text[:match.start()])
        else:
            subject = match.groupdict().get("subject") or _LEAD.sub("", text[match.end():])
            subject = subject.rstrip("的")
        subject = subject.strip(" \t\n:,.!?;")
        return subject if re.search(r"\w", subject) else ""
    return ""
