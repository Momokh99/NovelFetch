# AUR packaging

This directory holds PKGBUILDs for publishing NovelFetch and its bundled
dependencies to the [Arch User Repository](https://aur.archlinux.org).

## Packages

| Package | Purpose |
|---------|---------|
| `novelfetch/` | The NovelFetch Textual TUI (runtime deps from [extra] + `python-deep-translator`) |
| `python-deep-translator/` | Companion package: `deep-translator` (no stable Arch/AUR package exists; only an unstable `-git`). |

### Why `python-deep-translator`

`deep-translator` is a hard TUI dependency (imported at module load by
`tui/reader.py` and `tui/download.py`) but has no stable package in [extra]
or the AUR. `novelfetch` therefore depends on this companion package.

### Why TUI-only on Arch

The GUI frontend needs **KivyMD ≥ 2.0.0**, which is not packaged for Arch
(the AUR `python-kivymd` is stuck at 1.2.0). The `novelfetch-gui` console
script is removed at install time so users don't hit a confusing ImportError.
`python-kivy` and `python-kivymd` remain listed as `optdepends` for when a
modern KivyMD package appears.

## Layout

Each directory is a self-contained AUR package: a `PKGBUILD` plus its
generated `.SRCINFO`. The `.SRCINFO` is produced by:

```sh
makepkg --printsrcinfo > .SRCINFO
```

## Local verification

From a package directory:

```sh
makepkg -sf          # download sources, build, package
makepkg --printsrcinfo > .SRCINFO   # regenerate metadata when editing
```

Requires `python-build`, `python-installer`, and the relevant `makedepends`
from [extra].

## Publishing

You need an AUR account with an SSH key registered (separate from GitHub).
Create a repo on AUR for each package (`python-deep-translator` first, since
`novelfetch` depends on it), then:

```sh
# python-deep-translator
git clone ssh://aur@aur.archlinux.org/python-deep-translator.git /tmp/aur-pdt
cp -r packaging/aur/python-deep-translator/. /tmp/aur-pdt/
cd /tmp/aur-pdt && rm -rf src pkg *.tar.gz
makepkg --printsrcinfo > .SRCINFO
git add -A && git commit -m "Initial release" && git push

# novelfetch (after python-deep-translator is live)
git clone ssh://aur@aur.archlinux.org/novelfetch.git /tmp/aur-nf
cp -r packaging/aur/novelfetch/. /tmp/aur-nf/
cd /tmp/aur-nf && rm -rf src pkg *.tar.gz
makepkg --printsrcinfo > .SRCINFO
git add -A && git commit -m "Initial release" && git push
```

## Release workflow note

`novelfetch` sources the GitHub **release tarball**
(`novelfetch-<ver>.tar.gz`), so its `pkgver`, source URL, and `sha256sum`
must be updated in lockstep with each upstream release. The data-path fix in
`core/paths.py`/`tui/main.py` is essential: it routes user data to
`~/.novelfetch` instead of the (read-only, root-owned) site-packages dir.
