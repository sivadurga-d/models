#!/usr/bin/env python3
"""
Sync model IDs from a pricing JSON file to the corresponding general JSON file.
For each model present in pricing but missing in general, adds a minimal stub at the end.
Existing file content (formatting, key order, all existing entries) is left unchanged;
only the new model stubs are appended before the root closing brace.
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
    "removeParams": [ "top_p"]
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

        content = general_path.read_text()
        general = json.loads(content)
        general_models = set(k for k in general.keys() if k not in GENERAL_RESERVED)
        # Only add model IDs; exclude reserved keys (name, description, default) so they are never added or overwritten.
        missing = sorted(pricing_models - general_models - GENERAL_RESERVED)

        if not missing:
            print(f"All pricing models already present in {general_path}")
            continue

        # Detect indent from file (e.g. "  \"key\"" -> 2 spaces).
        indent = "  "
        for line in content.splitlines():
            stripped = line.lstrip()
            if stripped.startswith('"') and ":" in stripped:
                indent = line[: line.index('"')]
                break

        # Build the new entries string (script-formatted only for the added stubs).
        stub_json = json.dumps(MINIMAL_STUB, indent=2)
        stub_lines = stub_json.splitlines()
        new_entries = []
        for model_id in missing:
            # One entry: indent + "id": { ... } with inner lines indented
            inner = "\n".join(indent + line for line in stub_lines[1:])
            new_entries.append(f'{indent}"{model_id}": {{\n{inner}')
        new_entries_str = ",\n".join(new_entries)

        # Insert before the root closing "}": put comma on the last model's line, then new entries.
        root_close = len(content) - 1
        while root_close >= 0 and content[root_close] in " \t\n\r":
            root_close -= 1
        if root_close < 0 or content[root_close] != "}":
            print(f"::warning::Could not find root closing brace in {general_path}, skipping", file=sys.stderr)
            continue
        # Newline before root "}" is at root_close - 1; insert after last "}" so comma is on that line.
        insert_at = root_close - 1
        if insert_at < 0 or content[insert_at] != "\n":
            print(f"::warning::Unexpected format before root brace in {general_path}, skipping", file=sys.stderr)
            continue
        content = content[: insert_at] + ",\n" + new_entries_str + "\n" + content[insert_at :]

        general_path.write_text(content)

        print(f"Added missing models to {general_path}:")
        for m in missing:
            print(f"  - {m}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
