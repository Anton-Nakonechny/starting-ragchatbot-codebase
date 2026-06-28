#!/usr/bin/env bash
# format.sh — run code formatting and linting checks for the project.
#
# Usage:
#   ./scripts/format.sh          # format + lint (fix in place)
#   ./scripts/format.sh --check  # check only, exit non-zero if changes needed

set -euo pipefail

CHECK=""
if [[ "${1:-}" == "--check" ]]; then
  CHECK="--check"
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> black: formatting Python files"
uv run black $CHECK backend/

echo "==> ruff: linting Python files"
uv run ruff check ${CHECK:---fix} backend/

echo "==> Done."
