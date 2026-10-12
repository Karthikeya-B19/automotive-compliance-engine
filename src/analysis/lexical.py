"""Offset-preserving C/C++ lexical masking, not a compiler/preprocessor."""
import re

TOKENS = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')


def mask_non_code(source: str, *, strings: bool = True) -> str:
    def replace(match: re.Match) -> str:
        token = match.group()
        if not strings and not token.startswith(("//", "/*")):
            return token
        return "".join("\n" if char == "\n" else " " for char in token)
    return TOKENS.sub(replace, source)
