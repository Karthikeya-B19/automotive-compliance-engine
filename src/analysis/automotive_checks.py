"""Explainable ECU review candidates with intentionally narrow syntactic scope."""
import re
from .lexical import mask_non_code


RULES = {
    "AUTO-DIV-ZERO": ("Literal division or modulo by zero", "Arithmetic safety", "Critical", "CWE-369", "Validate the denominator and define a safe fallback before dividing."),
    "AUTO-ARRAY-BOUND": ("Constant array index outside declared capacity", "Boundary safety", "High", "CWE-125", "Keep the index in [0, capacity) and test the boundary."),
    "AUTO-SHIFT-WIDTH": ("Shift count outside fixed-width operand range", "Arithmetic safety", "High", "CWE-758", "Validate the shift count against the operand width."),
    "AUTO-ASSIGN-COND": ("Assignment used as an if condition", "Control flow", "Medium", "CWE-481", "Confirm intent and use an explicit comparison where required."),
    "AUTO-FORMAT": ("Nonliteral printf format argument", "Input validation", "High", "CWE-134", "Use a constant format string and pass external text as an argument."),
    "AUTO-DOUBLE-FREE": ("Repeated free without reassignment", "Resource management", "High", "CWE-415", "Give each allocation one owner and release it once."),
    "AUTO-USE-AFTER-FREE": ("Pointer access after free without reassignment", "Pointer safety", "High", "CWE-416", "Remove accesses after release and clarify object lifetime."),
    "AUTO-ISR-HEAP": ("Dynamic allocation in interrupt-style function", "Real-time safety", "Medium", "CWE-400", "Use preallocated storage and measure worst-case interrupt latency."),
    "AUTO-ISR-BLOCK": ("Blocking call in interrupt-style function", "Real-time safety", "Medium", "CWE-833", "Defer blocking work to a task and bound interrupt execution time."),
    "AUTO-RECURSION": ("Direct recursion requires stack bound review", "Real-time safety", "Medium", "CWE-674", "Use bounded iteration or prove maximum recursion depth and stack usage."),
    "AUTO-CAN-DLC": ("Classical CAN DLC exceeds eight bytes", "Protocol safety", "High", "CWE-20", "Validate classical CAN DLC in [0, 8]. Confirm CAN FD context separately."),
    "AUTO-BUSY-WAIT": ("Empty unbounded busy-wait loop", "Real-time safety", "Medium", "CWE-835", "Add a timeout, watchdog strategy, or bounded scheduler wait."),
    "AUTO-SHELL": ("Shell command execution in embedded source", "Input validation", "High", "CWE-78", "Avoid shell execution or use a tightly constrained approved interface."),
}


def automotive_candidates(source: str, functions: list[dict]) -> list[dict]:
    code = mask_non_code(source)
    original = source.splitlines()
    candidates = []

    def add(rule, offset):
        line = code.count("\n", 0, offset) + 1
        function = next((f["name"] for f in functions if f["start_line"] <= line <= f["end_line"]), None)
        title, category, severity, cwe, recommendation = RULES[rule]
        candidates.append(dict(rule_id=rule, title=title, category=category, severity=severity,
                               cwe=cwe, recommendation=recommendation, line=line,
                               function=function, evidence=original[line - 1]))

    patterns = {
        "AUTO-DIV-ZERO": r"(?<!/)[/%]\s*\(?\s*0(?:[uUlL]*)\s*\)?\s*(?=[;,)\n])",
        "AUTO-ASSIGN-COND": r"\bif\s*\(\s*[A-Za-z_]\w*\s*=(?!=)",
        "AUTO-FORMAT": r"\bprintf\s*\(\s*[A-Za-z_]\w*\s*[,)]",
        "AUTO-CAN-DLC": r"\b(?:[A-Za-z_]\w*\s*(?:\.|->)\s*)?can_dlc\s*=\s*(?:9|[1-9]\d+)[uUlL]*\s*;",
        "AUTO-BUSY-WAIT": r"\bwhile\s*\(\s*(?:1|true)\s*\)\s*(?:;|\{\s*\})",
        "AUTO-SHELL": r"\b(?:system|popen)\s*\(",
    }
    for rule, pattern in patterns.items():
        for match in re.finditer(pattern, code):
            add(rule, match.start())

    # Restrict variable state to one function. This does not model aliases or branches.
    for function in functions:
        begin = sum(len(line) for line in code.splitlines(keepends=True)[:function["start_line"] - 1])
        end = sum(len(line) for line in code.splitlines(keepends=True)[:function["end_line"]])
        body = code[begin:end]
        arrays = {}
        widths = {}
        released = set()
        for match in re.finditer(r"[^;\n]+[;\n]?", body):
            statement = match.group()
            offset = begin + match.start()
            declaration = re.search(r"\b(?:char|int|float|double|u?int\d+_t)\s+(\w+)\s*\[\s*(\d+)\s*\]", statement)
            if declaration:
                arrays[declaration[1]] = int(declaration[2])
            for access in re.finditer(r"\b(\w+)\s*\[\s*(-?\d+)\s*\]", statement):
                if declaration and access.start() >= declaration.start() and access[1] == declaration[1]:
                    continue
                if access[1] in arrays and not 0 <= int(access[2]) < arrays[access[1]]:
                    add("AUTO-ARRAY-BOUND", offset + access.start())
            width = re.search(r"\b(u?int(8|16|32|64)_t)\s+(\w+)\b", statement)
            if width:
                widths[width[3]] = max(32, int(width[2]))  # integer promotion, assumes 32-bit int target
            for shift in re.finditer(r"\b(\w+)\s*(?:<<|>>)\s*(-?\d+)", statement):
                if shift[1] in widths and not 0 <= int(shift[2]) < widths[shift[1]]:
                    add("AUTO-SHIFT-WIDTH", offset + shift.start())
            for var in list(released):
                if re.search(rf"\b{re.escape(var)}\s*=(?!=)", statement):
                    released.remove(var)
                    continue
                if re.search(rf"\bfree\s*\(\s*{re.escape(var)}\s*\)", statement):
                    add("AUTO-DOUBLE-FREE", offset)
                elif re.search(rf"(?:\*\s*{re.escape(var)}\b|\b{re.escape(var)}\s*(?:->|\[))", statement):
                    add("AUTO-USE-AFTER-FREE", offset)
            freed = re.search(r"\bfree\s*\(\s*(\w+)\s*\)", statement)
            if freed:
                released.add(freed[1])
        name = function["name"]
        brace = body.find("{")
        executable = body[brace + 1:]
        if re.search(rf"\b{re.escape(name)}\s*\(", executable):
            add("AUTO-RECURSION", begin + brace + 1 + re.search(rf"\b{re.escape(name)}\s*\(", executable).start())
        if re.search(r"(?:IRQHandler|ISR|interrupt)", name, re.I):
            for pattern, rule in [(r"\b(?:malloc|calloc|realloc)\s*\(", "AUTO-ISR-HEAP"),
                                  (r"\b(?:sleep|usleep|delay|HAL_Delay)\s*\(", "AUTO-ISR-BLOCK")]:
                for call in re.finditer(pattern, executable):
                    add(rule, begin + brace + 1 + call.start())
    return candidates
