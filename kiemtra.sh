#!/bin/bash
# Chay check tra cuc bo thay cho CI. Dung truoc moi lan push.
set -e
V=.venv/bin
echo "1/3 Kiem dinh dang"; $V/ruff format --check src tests
echo "2/3 Lint";           $V/ruff check src tests
echo "3/3 Kiem thu";       $V/pytest -q
echo "Tat ca deu dat."
