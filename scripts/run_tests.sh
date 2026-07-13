#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../backend"
pip install -r requirements.txt --break-system-packages -q
pytest
