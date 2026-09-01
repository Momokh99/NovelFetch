#!/usr/bin/env python3
"""Release version helpers for NovelFetch.

Used by the GitHub Actions release workflow and `make bump-release`:

  * --check        resolve the release version and, on tag runs, fail if it
                   disagrees with pyproject.toml / buildozer.spec. Prints the
                   resolved version to stdout.
  * --bump X.Y.Z   rewrite the version in pyproject.toml and buildozer.spec.
"""

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
BUILDOZER = ROOT / "buildozer.spec"


def _read_versions():
    pyproject_m = re.search(
        r'^version\s*=\s*"([^"]+)"\s*$', PYPROJECT.read_text(), re.M
    )
    buildozer_m = re.search(
        r"^version\s*=\s*([0-9][0-9.]*)\s*$", BUILDOZER.read_text(), re.M
    )
    if not pyproject_m or not buildozer_m:
        raise SystemExit(
            f"could not parse versions (pyproject={pyproject_m and pyproject_m.group(1)!r}, "
            f"buildozer={buildozer_m and buildozer_m.group(1)!r})"
        )
    return pyproject_m.group(1), buildozer_m.group(1)


def _check(args):
    pyver, bzver = _read_versions()

    ref_type = args.tag_type or os.environ.get("GITHUB_REF_TYPE", "")
    ref_name = args.tag or os.environ.get("GITHUB_REF_NAME", "")

    if ref_type == "tag":
        if not ref_name.startswith("v"):
            raise SystemExit(f"expected tag of the form vX.Y.Z, got {ref_name!r}")
        tag_version = ref_name[1:]
        # Semver prereleases (v1.2.3-beta.1) carry a suffix; the packaged
        # version fields only store the numeric core X.Y.Z.
        core = tag_version.split("-", 1)[0]
        if not (core == pyver == bzver):
            raise SystemExit(
                f"version mismatch: tag {core!r} != pyproject {pyver!r} !="
                f" buildozer {bzver!r}"
            )
        print(core)
    else:
        # Manual dispatch (or a local run): pyproject.toml is the source of
        # truth, but the other version fields must still agree.
        if pyver != bzver:
            raise SystemExit(
                f"version mismatch: pyproject {pyver!r} != buildozer {bzver!r}"
            )
        print(pyver)


def _bump(args):
    version = args.bump
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"invalid version {version!r}; expected X.Y.Z")

    pyproject = PYPROJECT.read_text()
    if not re.search(r'^version\s*=\s*"([^"]+)"\s*$', pyproject, re.M):
        raise SystemExit("pyproject.toml: no [project] version found to bump")
    PYPROJECT.write_text(
        re.sub(
            r'^version\s*=\s*"[^"]+"\s*$',
            f'version = "{version}"',
            pyproject,
            count=1,
            flags=re.M,
        )
    )

    buildozer = BUILDOZER.read_text()
    if not re.search(r"^version\s*=\s*([0-9][0-9.]*)\s*$", buildozer, re.M):
        raise SystemExit("buildozer.spec: no version found to bump")
    BUILDOZER.write_text(
        re.sub(
            r"^version\s*=\s*[0-9][0-9.]*\s*$",
            f"version = {version}",
            buildozer,
            count=1,
            flags=re.M,
        )
    )
    print(f"bumped version to {version} in pyproject.toml and buildozer.spec")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="resolve and validate the release version (default when --bump is absent)",
    )
    parser.add_argument(
        "--tag",
        metavar="vX.Y.Z",
        help="tag to validate against (default: $GITHUB_REF_NAME)",
    )
    parser.add_argument(
        "--tag-type",
        default=None,
        help="ref type to validate as (default: $GITHUB_REF_TYPE)",
    )
    parser.add_argument(
        "--bump",
        metavar="X.Y.Z",
        help="rewrite versions in pyproject.toml and buildozer.spec",
    )
    args = parser.parse_args()

    if args.bump:
        _bump(args)
    else:
        _check(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
