"""Privilege helpers: pkexec elevation + per-user config dir.

The GUI stays unprivileged (Wayland-safe) and elevates only the tiny CLI
writer via pkexec, which pops a native GNOME password dialog.
"""
import os
import pwd
import shutil
import subprocess
import sys


def user_home():
    """Real user's home even when running under sudo/pkexec as root."""
    if os.geteuid() == 0:
        for var in ("PKEXEC_UID", "SUDO_UID"):
            uid = os.environ.get(var)
            if uid:
                try:
                    return pwd.getpwuid(int(uid)).pw_dir
                except (KeyError, ValueError):
                    pass
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user:
            try:
                return pwd.getpwnam(sudo_user).pw_dir
            except KeyError:
                pass
    return os.path.expanduser("~")


def config_dir():
    return os.path.join(user_home(), ".config", "legion-rgb")


def device_writable(hidraw_path):
    return os.access(hidraw_path, os.W_OK)


def have_pkexec():
    return shutil.which("pkexec") is not None


def run_cli_elevated(cli_path, argv, timeout=30):
    """Run `pkexec <cli> <argv>`, raising on failure. Returns stdout."""
    cmd = ["pkexec", cli_path] + argv
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError("pkexec not found. Install policykit-1.")
    if r.returncode == 126 or r.returncode == 127:
        # user dismissed the auth dialog
        raise RuntimeError("Authorization dismissed.")
    if r.returncode != 0:
        err = (r.stderr or r.stdout or f"exit {r.returncode}").strip()
        raise RuntimeError(f"pkexec failed: {err}")
    return r.stdout.strip()


def pkexec_hint(cli_path, argv):
    quoted = " ".join(f"'{a}'" if " " in a else a for a in [cli_path] + argv)
    return f"pkexec {quoted}"
