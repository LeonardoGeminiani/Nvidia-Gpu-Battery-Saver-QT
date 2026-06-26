#!/bin/bash
# Creates a local venv with runtime deps for development.
set -e

python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

echo "Done. Run with:"
echo "  .venv/bin/python gui.py"
