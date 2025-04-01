#!/usr/bin/env bash

uv sync --frozen

uv run pre-commit install
