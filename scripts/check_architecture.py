import ast
from pathlib import Path
from typing import Dict, List, Set


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "pipeline"


def _module_name(path: Path) -> str:
    rel = path.relative_to(ROOT / "src")
    return ".".join(rel.with_suffix("").parts)


def _category(path: Path) -> str:
    rel = path.relative_to(SRC)
    parts = rel.parts
    if parts[0] == "stages":
        return f"stages.{parts[1].split('.')[0]}"
    if parts[0] == "domains":
        return f"domains.{parts[1]}"
    if parts[0] == "common":
        return "common"
    if parts[0] == "transforms":
        return "transforms"
    if parts[0] in {"contracts.py", "contracts"}:
        return "contracts"
    if parts[0] == "orchestrator.py":
        return "orchestrator"
    return "root"


def _imports(path: Path) -> Set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def main() -> int:
    violations: List[str] = []
    py_files = [p for p in SRC.rglob("*.py") if p.name != "__init__.py"]
    module_map: Dict[Path, str] = {p: _module_name(p) for p in py_files}

    for path, mod in module_map.items():
        cat = _category(path)
        imps = _imports(path)

        def add(msg: str) -> None:
            violations.append(f"{mod}: {msg}")

        # Common must not import stages or domains
        if cat == "common":
            if any(i.startswith("pipeline.stages") or i.startswith("pipeline.domains") for i in imps):
                add("common must not depend on stages/domains")

        # Domains must not import stages
        if cat.startswith("domains"):
            if any(i.startswith("pipeline.stages") for i in imps):
                add("domains must not depend on stages")

        # Stages must not import other stages directly
        if cat.startswith("stages."):
            for imp in imps:
                if imp.startswith("pipeline.stages"):
                    if not imp.startswith(f"pipeline.{cat}"):
                        add("stage must not depend on other stages")

        # Orchestrator must depend only on stages/contracts/common
        if cat == "orchestrator":
            for imp in imps:
                if imp.startswith("pipeline.domains") or imp.startswith("pipeline.transforms"):
                    add("orchestrator must not depend on domains/transforms")

    if violations:
        print("ARCHITECTURE CHECK FAILED")
        for v in violations:
            print(f"- {v}")
        return 1

    print("ARCHITECTURE CHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
