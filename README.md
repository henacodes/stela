# Stela

Stela is a desktop reader for PDF and EPUB books.

## Installation

### Linux

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/henacodes/stela/master/scripts/install.sh)
```

### Windows (PowerShell)

```powershell
iwr -useb https://raw.githubusercontent.com/henacodes/stela/master/scripts/install.ps1 | iex
```

Optional: install a specific release tag.

Linux:

```bash
TAG=v0.1.0 bash <(curl -fsSL https://raw.githubusercontent.com/henacodes/stela/master/scripts/install.sh)
```

Windows:

```powershell
$env:TAG="v0.1.0"; iwr -useb https://raw.githubusercontent.com/henacodes/stela/master/scripts/install.ps1 | iex
```

## Build from source

### Prerequisites

- Python 3.10+
- Flet CLI

### Run locally

```bash
uv run flet run
```

### Build desktop packages

Linux:

```bash
./scripts/release_build.sh linux
```

Windows:

```bash
./scripts/release_build.sh windows
```

Both:

```bash
./scripts/release_build.sh all
```

## Release flow

Release binaries are built by GitHub Actions on tag push using [/.github/workflows/release-build.yml](.github/workflows/release-build.yml).

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Run the app and verify behavior.
5. Open a pull request.

If your change affects build/install, update [README.md](README.md) and relevant scripts under [scripts](scripts).
