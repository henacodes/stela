# Stela app

## Run the app

### uv

Run as a desktop app:

```bash
uv run flet run
```

Run as a web app:

```bash
uv run flet run --web
```

For more details on running the app, refer to the [Getting Started Guide](https://flet.dev/docs/).

## Build the app

### Android

```bash
flet build apk -v
```

For more details on building and signing `.apk` or `.aab`, refer to the [Android Packaging Guide](https://flet.dev/docs/publish/android/).

### iOS

```bash
flet build ipa -v
```

For more details on building and signing `.ipa`, refer to the [iOS Packaging Guide](https://flet.dev/docs/publish/ios/).

### macOS

```bash
flet build macos -v
```

For more details on building macOS package, refer to the [macOS Packaging Guide](https://flet.dev/docs/publish/macos/).

### Linux

```bash
flet build linux -v
```

For more details on building Linux package, refer to the [Linux Packaging Guide](https://flet.dev/docs/publish/linux/).

### Windows

```bash
flet build windows -v
```

For more details on building Windows package, refer to the [Windows Packaging Guide](https://flet.dev/docs/publish/windows/).

### Web

```bash
flet build web -v
```

For more details on building Web app, refer to the [Web Packaging Guide](https://flet.dev/docs/publish/web/).

## File associations (Open With)

Yes, this is now designed to be installer-driven (no end-user scripts required).

## One-command release build

Use [scripts/release_build.sh](scripts/release_build.sh):

```bash
./scripts/release_build.sh linux
```

```bash
./scripts/release_build.sh windows
```

```bash
./scripts/release_build.sh all
```

This runs platform builds and (for Windows) attempts installer generation via Inno Setup if `iscc` is installed.

Bundled assets are included in project:
- Linux desktop entry: [packaging/linux/stela.desktop](packaging/linux/stela.desktop)
- Linux package maintainer hooks: [packaging/linux/debian/postinst](packaging/linux/debian/postinst), [packaging/linux/debian/postrm](packaging/linux/debian/postrm)
- Windows installer script: [packaging/windows/stela.iss](packaging/windows/stela.iss)
- Windows registry fallback template: [packaging/windows/register_associations.reg](packaging/windows/register_associations.reg)

### Linux

- Ship the `.desktop` file in the package under `/usr/share/applications/`.
- `postinst`/`postrm` refresh desktop+MIME caches during install/remove.
- End users should only install/uninstall the package.

Optional dev-only helper remains available at [packaging/linux/register_associations.sh](packaging/linux/register_associations.sh).

### Windows

- Use [packaging/windows/stela.iss](packaging/windows/stela.iss) to create an installer that writes Open With registry entries during install.
- End users just run the installer.

Fallback/manual method is kept in [packaging/windows/register_associations.reg](packaging/windows/register_associations.reg).

### Runtime behavior

When the OS opens a `.pdf` or `.epub` with Stela, the passed file path is now accepted at startup, imported/updated in the local DB, and opened directly in the reader.
