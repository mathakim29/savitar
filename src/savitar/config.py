"""Settings from the user's pyproject.toml:

[tool.savitar]
web = "web"          # frontend folder (relative to pyproject.toml)
dev = false          # true = watch + rebuild (single process only)
packages = []        # extra JS packages, managed by `savitar pkg add/remove`
"""

import os
from pathlib import Path

import tomlkit

TRUE = {"1", "true", "yes", "on"}


def _plain(x):
    return x.unwrap() if hasattr(x, "unwrap") else x


def find_pyproject():
    here = Path.cwd().resolve()
    for d in (here, *here.parents):
        f = d / "pyproject.toml"
        if f.exists():
            return f
    return None


def load():
    """-> ([tool.savitar] settings, project root)"""
    f = find_pyproject()
    if not f:
        return {}, Path.cwd().resolve()
    doc = tomlkit.parse(f.read_text())
    cfg = _plain(doc.get("tool", {}).get("savitar", {}))
    return cfg, f.parent


def resolve_dev(arg, cfg):
    """kwarg > env SAVITAR_DEV > pyproject [tool.savitar] dev > False"""
    if arg is not None:
        return bool(arg)
    env = os.environ.get("SAVITAR_DEV")
    if env is not None:
        return env.strip().lower() in TRUE
    return bool(cfg.get("dev", False))


def pkg_name(spec):
    """'blockly@11' -> 'blockly', '@scope/x@1' -> '@scope/x'"""
    i = spec.rfind("@")
    return spec if i <= 0 else spec[:i]


def _edit_packages(fn):
    f = find_pyproject()
    if not f:
        print("savitar: no pyproject.toml found, package not recorded")
        return
    doc = tomlkit.parse(f.read_text())
    if "tool" not in doc:
        doc["tool"] = tomlkit.table(True)
    if "savitar" not in doc["tool"]:
        doc["tool"]["savitar"] = tomlkit.table()
    sv = doc["tool"]["savitar"]
    items = [str(x) for x in sv.get("packages", [])]
    arr = tomlkit.array()
    arr.extend(fn(items))
    sv["packages"] = arr
    f.write_text(tomlkit.dumps(doc))
    print(f"savitar: recorded in {f} ([tool.savitar] packages)")


def add_packages(specs):
    names = {pkg_name(s) for s in specs}
    _edit_packages(lambda items: [i for i in items if pkg_name(i) not in names] + list(specs))


def remove_packages(names):
    gone = {pkg_name(n) for n in names}
    _edit_packages(lambda items: [i for i in items if pkg_name(i) not in gone])
