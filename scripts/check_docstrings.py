"""Check (and optionally fix) missing one-line docstrings on public functions and classes under src/.

Usage:
    python scripts/check_docstrings.py          # list problems
    python scripts/check_docstrings.py --fix    # insert a one-line docstring built from the name
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def missing(path: Path) -> list[ast.AST]:
    """Public functions and classes in a file that have no docstring."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        and not n.name.startswith("_")
        and ast.get_docstring(n) is None
    ]


def docstring_for(name: str) -> str:
    """Build a one-line docstring from an identifier."""
    words = name.replace("_", " ").strip()
    return f"{words[:1].upper()}{words[1:]}."


def fix_file(path: Path, nodes: list[ast.AST]) -> int:
    """Insert docstrings (bottom-up so line numbers stay valid); returns how many were inserted."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    done = 0
    for node in sorted(nodes, key=lambda n: n.body[0].lineno, reverse=True):
        first = node.body[0]
        if (
            first.lineno == node.lineno
        ):  # one-line body such as `def f(): return 1`; skip
            continue
        indent = " " * first.col_offset
        lines.insert(first.lineno - 1, f'{indent}"""{docstring_for(node.name)}"""\n')
        done += 1
    path.write_text("".join(lines), encoding="utf-8")
    return done


def main() -> None:
    """Scan src/ and report or fix missing docstrings."""
    fix = "--fix" in sys.argv
    total = fixed = 0
    for path in sorted((ROOT / "src").rglob("*.py")):
        nodes = missing(path)
        if not nodes:
            continue
        total += len(nodes)
        if fix:
            fixed += fix_file(path, nodes)
        else:
            for n in nodes:
                print(f"{path.relative_to(ROOT)}:{n.lineno}  {n.name}")
    print(f"missing docstrings: {total}" + (f" | inserted: {fixed}" if fix else ""))
    sys.exit(0 if total == 0 or fix else 1)


if __name__ == "__main__":
    main()
