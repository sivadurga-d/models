#!/usr/bin/env python3
"""
Sync model IDs from a pricing JSON file to the corresponding general JSON file.
For each model present in pricing but missing in general, adds a minimal stub.
Uses JSON only (no text manipulation); run `npm run format` after to format files.
Usage: sync_pricing_to_general.py <pricing-file> [general-file]
If general-file is omitted, inferred from pricing path (e.g. pricing/google.json -> general/google.json).
"""

import json
import sys
from pathlib import Path

# Keys that exist in both pricing and general but must never be synced or overwritten.
GENERAL_RESERVED = {"name", "description", "default"}
# Only max_tokens; exclude top_k, top_p, log_p, etc. from minimal stub
MINIMAL_STUB = {
    "params": [{"key": "max_tokens", "maxValue": 64000}],
    "type": {"primary": "chat", "supported": ["image", "pdf", "doc", "tools"]},
    "removeParams": ["top_p"],
}


def get_general_paths(pricing_path: Path, general_path_arg: Path | None) -> list[Path]:
    """Resolve which general file(s) to sync to. OpenAI pricing syncs to both openai and open-ai."""
    if general_path_arg is not None:
        return [general_path_arg]
    basename = pricing_path.stem  # e.g. "openai"
    if basename == "openai":
        return [Path("general/openai.json"), Path("general/open-ai.json")]
    return [Path("general") / pricing_path.name]


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: sync_pricing_to_general.py <pricing-file> [general-file]", file=sys.stderr)
        return 1

    pricing_path = Path(sys.argv[1])
    general_path_arg = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    if not pricing_path.exists():
        print(f"::error file={pricing_path}::Pricing file not found", file=sys.stderr)
        return 1

    general_paths = get_general_paths(pricing_path, general_path_arg)
    pricing = json.loads(pricing_path.read_text())
    pricing_models = set(pricing.keys())

    for general_path in general_paths:
        if not general_path.exists():
            print(f"::notice::No general file at {general_path}, skipping")
            continue

        general = json.loads(general_path.read_text())
        general_models = set(k for k in general.keys() if k not in GENERAL_RESERVED)
        # Only add model IDs; exclude reserved keys (name, description, default) so they are never added or overwritten.
        missing = sorted(pricing_models - general_models - GENERAL_RESERVED)

        if not missing:
            print(f"All pricing models already present in {general_path}")
            continue

        # Build output from existing general; only add new keys for missing models.
        output = dict(general)
        for model_id in missing:
            output[model_id] = dict(MINIMAL_STUB)

        with open(general_path, "w") as f:
            json.dump(output, f, indent=2)
            f.write("\n")

        print(f"Added missing models to {general_path}:")
        for m in missing:
            print(f"  - {m}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
