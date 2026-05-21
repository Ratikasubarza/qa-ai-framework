"""
AST security pre-flight for LLM-generated test code.

Called before any generated Python file is written to disk and before it is
executed via subprocess.  Rejects code that imports blocked OS/network modules
or calls dangerous builtins (eval, exec, open, __import__).

The allowlist is intentionally conservative.  Test files need pytest, httpx,
playwright, appium, allure, structlog, and config imports — nothing else.
"""
from __future__ import annotations

import ast

import structlog

from core.exceptions import CodeGenerationSecurityError

logger = structlog.get_logger(__name__)

# Top-level modules that generated test code must never import
_BLOCKED_IMPORTS: frozenset[str] = frozenset({
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "http",
    "urllib",
    "ftplib",
    "smtplib",
    "importlib",
    "ctypes",
    "pickle",
    "marshal",
    "builtins",
    "threading",
    "multiprocessing",
    "signal",
    "pty",
    "tty",
    "termios",
    "code",
    "codeop",
    "compileall",
    "py_compile",
})

# Built-in calls that must never appear in generated test code
_BLOCKED_CALLS: frozenset[str] = frozenset({
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "breakpoint",
    "input",
})


def validate_generated_code(source_code: str, file_path: str) -> None:
    """
    Parse and AST-scan LLM-generated test code before writing to disk.

    Raises CodeGenerationSecurityError listing every violation found.
    Logs a structured audit event on both pass and fail.
    """
    try:
        tree = ast.parse(source_code, filename=file_path, mode="exec")
    except SyntaxError as exc:
        raise CodeGenerationSecurityError(
            f"Generated code has syntax errors: {exc}",
            context={"file": file_path, "syntax_error": str(exc)},
        ) from exc

    violations: list[str] = []

    for node in ast.walk(tree):
        # ── Import statements ──────────────────────────────────────────────
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BLOCKED_IMPORTS:
                    violations.append(
                        f"Line {node.lineno}: blocked import '{alias.name}'"
                    )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in _BLOCKED_IMPORTS:
                    violations.append(
                        f"Line {node.lineno}: blocked 'from {node.module} import ...'"
                    )

        # ── Dangerous call sites ───────────────────────────────────────────
        elif isinstance(node, ast.Call):
            func_name: str | None = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name and func_name in _BLOCKED_CALLS:
                violations.append(
                    f"Line {node.lineno}: blocked call '{func_name}()'"
                )

    if violations:
        logger.error(
            "generated_code_security_violation",
            file=file_path,
            violation_count=len(violations),
            violations=violations,
        )
        raise CodeGenerationSecurityError(
            f"Generated code failed security pre-flight "
            f"({len(violations)} violation(s) in '{file_path}').",
            context={"file": file_path, "violations": violations},
        )

    logger.info(
        "generated_code_security_passed",
        file=file_path,
        nodes_checked=sum(1 for _ in ast.walk(tree)),
    )
