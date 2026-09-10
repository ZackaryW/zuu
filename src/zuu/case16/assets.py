"""Select raw binaries by common Rust target suffixes, independent of project name."""

from __future__ import annotations

from . import ReleaseAsset, ReleaseResolverError, _text


_ARCHITECTURES = {
    "x86_64": "x86_64", "amd64": "x86_64", "x64": "x86_64",
    "aarch64": "aarch64", "arm64": "aarch64",
    "x86": "i686", "i386": "i686", "i686": "i686",
}


def select_rust_asset(
    assets: tuple[ReleaseAsset, ...], system: str, machine: str
) -> ReleaseAsset:
    """Select one raw binary by Rust target suffix without assuming its prefix.

    Recognize x86_64/AMD64, aarch64/ARM64, and x86/i386/i686 aliases. Prefer native
    macOS over universal, Windows MSVC over GNU, and Linux musl over GNU. Ignore
    archives and sidecars through exact filename-ending matching. Equal-ranked
    matches, unsupported platforms, and missing binaries raise an error.
    """
    system = _text(system, "system")
    machine = _text(machine, "machine")
    arch = _ARCHITECTURES.get(machine.lower())
    if system.lower() == "darwin" and arch in ("aarch64", "x86_64"):
        suffixes = (f"{arch}-apple-darwin", "universal-apple-darwin")
    elif system.lower() == "windows" and arch is not None:
        suffixes = (f"{arch}-pc-windows-msvc.exe", f"{arch}-pc-windows-gnu.exe")
    elif system.lower() == "linux" and arch is not None:
        suffixes = (f"{arch}-unknown-linux-musl", f"{arch}-unknown-linux-gnu")
    else:
        raise ReleaseResolverError(f"unsupported Rust platform ({system}, {machine})")

    for suffix in suffixes:
        matches = [
            asset for asset in assets
            if asset.name.lower() == suffix or asset.name.lower().endswith("-" + suffix)
        ]
        if len(matches) > 1:
            names = ", ".join(asset.name for asset in matches)
            raise ReleaseResolverError(f"ambiguous assets for ({system}, {machine}): {names}")
        if matches:
            return matches[0]
    raise ReleaseResolverError(f"no matching Rust binary for ({system}, {machine})")
