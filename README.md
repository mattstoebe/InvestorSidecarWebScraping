# Investor Sidecar Web Scraping

Container-first web scraping workspace using Docker, Mise, and UV.

## Principles

- No host Python tooling required.
- Python and UV are installed inside the container with Mise.
- Dependencies are managed by UV from `pyproject.toml`.
- Focus is web scraping and saving results.

## Prerequisites

- Docker + Docker Compose
- GNU Make

## Setup

1. Copy environment template:

```sh
cp docker/vars.env-template docker/vars.env
```

2. Build and start container, then install dev extras:

```sh
make init
```

## Common Commands

- Show targets:

```sh
make help
```

- Open shell in container:

```sh
make shell
```

- Open root shell in container:

```sh
make root
```

- Run notebook server from container:

```sh
make notebook
```

- Stop containers:

```sh
make stop
```

- Remove containers/network:

```sh
make clean
```

## Notes

- `Makefile` and `devtools.mk` run commands in the running container.
- `docker/pythonenv/Dockerfile` installs `python` and `uv` via Mise.
- Base dependencies are installed during image build with `uv sync --no-dev`.
- Dev dependencies (notebook, lint/type/test tools) are installed with `make install-dev`.