#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import subprocess
import sys
from pathlib import Path


def _load_local_env() -> bool:
    """Load key/value pairs from .env into the process environment."""
    loaded = False
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return loaded

    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value
            loaded = True

    return loaded


def _add_venv_site_packages() -> bool:
    """Add site-packages from common local virtualenv locations."""
    added = False
    base_dir = Path(__file__).resolve().parent
    project_name = base_dir.name

    venv_roots = [
        base_dir / ".venv",
        base_dir / "venv",
        base_dir / "env",
    ]
    venv_roots.extend(Path.home().glob(f".local/share/virtualenvs/{project_name}-*"))

    for venv_root in venv_roots:
        lib_dir = venv_root / "lib"
        if not lib_dir.exists():
            continue
        for site_packages in sorted(lib_dir.glob("python*/site-packages")):
            site_packages_str = str(site_packages)
            if site_packages_str not in sys.path and site_packages.exists():
                sys.path.insert(0, site_packages_str)
                added = True

    return added


def _reexec_with_pipenv() -> bool:
    """Re-run manage.py with the project's Pipenv interpreter if available."""
    if os.environ.get("STORE_FRONT_REEXEC") == "1":
        return False

    try:
        venv_path = subprocess.check_output(
            ["pipenv", "--venv"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return False

    python_path = Path(venv_path) / "bin" / "python"
    if not python_path.exists():
        return False

    if Path(sys.executable).resolve() == python_path.resolve():
        return False

    env = os.environ.copy()
    env["STORE_FRONT_REEXEC"] = "1"
    os.execve(str(python_path), [str(python_path), *sys.argv], env)
    return True


def _reexec_with_dyld() -> bool:
    """Restart once when DYLD_LIBRARY_PATH is newly loaded from .env."""
    if os.environ.get("STORE_FRONT_DYLD_REEXEC") == "1":
        return False
    if "DYLD_LIBRARY_PATH" not in os.environ:
        return False

    env = os.environ.copy()
    env["STORE_FRONT_DYLD_REEXEC"] = "1"
    os.execve(sys.executable, [sys.executable, *sys.argv], env)
    return True


def main():
    """Run administrative tasks."""
    loaded_env = _load_local_env()
    if loaded_env and _reexec_with_dyld():
        return

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'storefront.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        if _add_venv_site_packages():
            try:
                from django.core.management import execute_from_command_line
            except ImportError:
                pass
            else:
                execute_from_command_line(sys.argv)
                return
        if _reexec_with_pipenv():
            return
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
