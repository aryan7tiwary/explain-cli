import re


_SPECIAL_MAP = {
    '^': "start of line",
    '$': "end of line",
    '.': "any single character",
    '*': "zero or more of previous",
    '+': "one or more of previous",
    '?': "zero or one (optional)",
    '|': "alternation (or)",
}


def looks_like_regex(text: str) -> bool:
    if not text:
        return False
    if text == '|' or text.startswith('-'):
        return False
    # Paths or URLs: treat as non-regex
    if '/' in text:
        return False
    # Pure IPv4 literal
    if re.fullmatch(r"\d+(?:\.\d+){3}", text):
        return False
    # Clear regex signals
    if text.startswith('^') or text.endswith('$'):
        return True
    if any(ch in text for ch in ['[', ']', '(', ')', '|', '{', '}']):
        return True
    # Quantifiers not escaped
    if re.search(r'(?<!\\)[*+?]', text):
        return True
    # Unescaped dot used outside of obvious IPs/paths
    if re.search(r'(?<!\\)\.', text):
        return True
    return False


def explain_regex(pattern: str) -> str:
    """Return a concise human explanation for simple regex patterns.

    This is heuristic and aims to be short and helpful.
    """
    try:
        # Basic high-level cases
        explanation_parts = []
        if pattern.startswith('^'):
            explanation_parts.append(_SPECIAL_MAP['^'])
            pattern = pattern[1:]
        if pattern.endswith('$'):
            explanation_parts.append(_SPECIAL_MAP['$'])
            pattern = pattern[:-1]

        # Character class like ^-[A-Z]
        desc = None
        if pattern.startswith('[') and pattern.endswith(']'):
            content = pattern[1:-1]
            if content.startswith('^'):
                desc = f"not any of '{content[1:]}'"
            else:
                desc = f"one of '{content}'"
        elif pattern.startswith('\\') and len(pattern) == 2:
            # escaped single char
            desc = f"literal '{pattern[1:]}'"
        elif pattern:
            # Plain text or simple metachars
            human = []
            i = 0
            while i < len(pattern):
                ch = pattern[i]
                nxt = pattern[i+1] if i+1 < len(pattern) else ''
                if ch == '[':
                    j = pattern.find(']', i+1)
                    if j != -1:
                        cls = pattern[i+1:j]
                        if cls.startswith('^'):
                            human.append(f"not any of '{cls[1:]}'")
                        else:
                            human.append(f"one of '{cls}'")
                        i = j + 1
                        continue
                if ch in _SPECIAL_MAP:
                    human.append(_SPECIAL_MAP[ch])
                elif ch == '\\' and nxt:
                    human.append(f"literal '{nxt}'")
                    i += 1
                else:
                    human.append(f"'{ch}'")
                i += 1
            if human:
                desc = ", ".join(human)

        if desc:
            if explanation_parts:
                return f"{', '.join(explanation_parts)}, then {desc}"
            return desc
        return "regular expression pattern"
    except Exception:
        return "regular expression pattern"


