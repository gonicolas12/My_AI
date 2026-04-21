"""
Wrapper exposing GUI syntax-highlighting helpers to the agents pane.

Exposes :
    SyntaxColorHelper : classe (ou None si l'import a échoué)
    SYNTAX_ANALYZER   : instance singleton utilisée pour tokeniser les lignes
    SYNTAX_AVAILABLE  : bool indiquant si le module est disponible
"""

try:
    from interfaces.gui.syntax_highlighting import \
        SyntaxHighlightingMixin as _SyntaxMixin

    class SyntaxColorHelper(_SyntaxMixin):
        """Wrapper exposing GUI syntax-highlighting helpers to the agents pane."""

        def __init__(self, colors):
            self.colors = colors

        def configure_tags(self, tw):
            """Configure all language colour tags on *tw*."""
            self._configure_formatting_tags(tw)  # pylint: disable=protected-access

        def highlight_line(self, tw, line, lang):
            """Tokenise *line* for *lang* and insert coloured spans into *tw*."""
            code_map = {}
            try:
                dispatch = {
                    "python":     self._analyze_python_tokens,
                    "javascript": self._analyze_javascript_tokens,
                    "js":         self._analyze_javascript_tokens,
                    "typescript": self._analyze_javascript_tokens,
                    "ts":         self._analyze_javascript_tokens,
                    "css":        self._analyze_css_tokens,
                    "html":       self._analyze_html_tokens,
                    "xml":        self._analyze_html_tokens,
                    "bash":       self._analyze_bash_tokens,
                    "shell":      self._analyze_bash_tokens,
                    "sh":         self._analyze_bash_tokens,
                    "sql":        self._analyze_sql_tokens,
                    "mysql":      self._analyze_sql_tokens,
                    "postgresql": self._analyze_sql_tokens,
                    "sqlite":     self._analyze_sql_tokens,
                    "java":       self._analyze_java_tokens,
                    "go":         self._analyze_go_tokens,
                    "golang":     self._analyze_go_tokens,
                    "ruby":       self._analyze_ruby_tokens,
                    "rb":         self._analyze_ruby_tokens,
                    "swift":      self._analyze_swift_tokens,
                    "php":        self._analyze_php_tokens,
                    "perl":       self._analyze_perl_tokens,
                    "pl":         self._analyze_perl_tokens,
                    "rust":       self._analyze_rust_tokens,
                    "rs":         self._analyze_rust_tokens,
                }  # pylint: disable=protected-access
                if lang in ("c", "cpp", "c++", "cxx"):
                    self._analyze_cpp_tokens(line, 0, code_map, lang)  # pylint: disable=protected-access
                elif lang in ("csharp", "cs", "c#"):
                    self._analyze_csharp_tokens(line, 0, code_map)  # pylint: disable=protected-access
                elif lang in dispatch:
                    dispatch[lang](line, 0, code_map)
                else:
                    tw.insert("end", line, "code_block")
                    return
            except Exception:
                tw.insert("end", line, "code_block")
                return

            n = len(line)
            i = 0
            while i < n:
                if i in code_map:
                    tag = code_map[i][1]
                    j = i + 1
                    while j < n and j in code_map and code_map[j][1] == tag:
                        j += 1
                    tw.insert("end", line[i:j], tag)
                    i = j
                else:
                    j = i + 1
                    while j < n and j not in code_map:
                        j += 1
                    tw.insert("end", line[i:j], "code_block")
                    i = j

    # Singleton used only for token analysis (no colors needed)
    SYNTAX_ANALYZER = SyntaxColorHelper({})
    SYNTAX_AVAILABLE = True
except Exception:
    SyntaxColorHelper = None  # type: ignore # pylint: disable=invalid-name
    SYNTAX_ANALYZER = None
    SYNTAX_AVAILABLE = False
