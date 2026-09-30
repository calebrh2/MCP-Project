FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /uvx /usr/local/bin/

ENV UV_LINK_MODE=copy \
    UV_PYTHON=/usr/local/bin/python \
    UV_PYTHON_DOWNLOADS=never
