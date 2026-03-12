import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline.orchestrator import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))

    result = run_pipeline(config, project_root=ROOT, publish=False)
    print(f"Smoke OK: df_final shape={result['df_final'].shape}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
