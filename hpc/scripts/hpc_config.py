#!/usr/bin/env python3
"""Idempotent cluster management for the Claude Code /hpc skill.

Usage:
  hpc_config.py list
  hpc_config.py detect-key
  hpc_config.py add <alias> <username> <host> [private_key_path]
  hpc_config.py remove <alias>
"""
import json
import re
import shutil
import sys
import time
from pathlib import Path

HOME = Path.home()
CONF_DIR = HOME / ".config" / "claude-hpc" / "clusters"
SSH_DIR = HOME / ".ssh"
SSH_CONF = SSH_DIR / "config"
CLAUDE_DIR = HOME / ".claude"
SETTINGS = CLAUDE_DIR / "settings.json"
CLAUDE_MD = CLAUDE_DIR / "CLAUDE.md"
KEY_PREFERENCE = ["id_ed25519", "id_ecdsa", "id_rsa"]
ALIAS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
GENERIC_ASK = ["Bash(sshfs *)", "Bash(sftp *)", "Bash(ssh-copy-id *)"]


def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def load_clusters():
    clusters = {}
    for f in sorted(CONF_DIR.glob("*.conf")):
        kv = dict(l.split("=", 1) for l in f.read_text().splitlines() if "=" in l)
        clusters[f.stem] = kv
    return clusters


def ask_rules(alias, host):
    return [f"Bash(ssh {alias}*)", f"Bash(ssh * {alias}*)", f"Bash(ssh *{host}*)",
            f"Bash(rsync *{alias}:*)", f"Bash(rsync *{host}*)",
            f"Bash(scp *{alias}:*)", f"Bash(scp *{host}*)"]


def ssh_markers(alias):
    return f"# >>> claude-hpc:{alias} >>>", f"# <<< claude-hpc:{alias} <<<"


def strip_block(text, begin, end):
    return re.sub(rf"^{re.escape(begin)}\n.*?^{re.escape(end)}\n*", "", text,
                  flags=re.S | re.M)


def write_ssh_block(alias, user, host, key):
    SSH_DIR.mkdir(mode=0o700, exist_ok=True)
    text = SSH_CONF.read_text() if SSH_CONF.exists() else ""
    if text:
        shutil.copy2(SSH_CONF, f"{SSH_CONF}.bak.{time.strftime('%Y%m%d%H%M%S')}")
    begin, end = ssh_markers(alias)
    text = strip_block(text, begin, end)
    text = strip_block(text, "# >>> claude-hpc >>>", "# <<< claude-hpc <<<")  # legacy format
    block = "\n".join([
        begin,
        f"Host {alias}",
        f"    HostName {host}",
        f"    User {user}",
        f"    IdentityFile {key}",
        "    IdentitiesOnly yes",
        "    ControlMaster auto",
        "    ControlPath ~/.ssh/cm-%C",
        "    ControlPersist 8h",
        "    ServerAliveInterval 60",
        "    ServerAliveCountMax 3",
        end, "", ""])
    # Prepend so it takes precedence over "Host *" blocks
    SSH_CONF.write_text(block + text if user else text)
    SSH_CONF.chmod(0o600)


def sync_safeguards(removed=None):
    """Regenerate ask rules and the CLAUDE.md block from the configured clusters."""
    clusters = load_clusters()
    CLAUDE_DIR.mkdir(exist_ok=True)

    s = json.loads(SETTINGS.read_text()) if SETTINGS.exists() and SETTINGS.stat().st_size else {}
    ask = s.setdefault("permissions", {}).setdefault("ask", [])
    if removed:
        drop = set(ask_rules(*removed)) | (set() if clusters else set(GENERIC_ASK))
        ask[:] = [r for r in ask if r not in drop]
    wanted = list(GENERIC_ASK) if clusters else []
    for a, c in clusters.items():
        wanted += ask_rules(a, c["HPC_HOST"])
    ask += [r for r in wanted if r not in ask]
    SETTINGS.write_text(json.dumps(s, indent=2) + "\n")

    begin, end = "<!-- # >>> claude-hpc >>> -->", "<!-- # <<< claude-hpc <<< -->"
    md = CLAUDE_MD.read_text() if CLAUDE_MD.exists() else ""
    md = strip_block(md, begin, end).rstrip("\n")
    if clusters:
        names = ", ".join(f"`{a}` ({c['HPC_HOST']})" for a, c in clusters.items())
        md += ("\n\n" if md else "") + "\n".join([
            begin,
            "# HPC clusters (/hpc skill)",
            f"- Configured clusters: {names}.",
            "- FORBIDDEN to connect to them (ssh, sshfs, rsync, scp) unless the user explicitly asks "
            "in the current session or invokes `/hpc`. Also applies in auto mode and to subagents. "
            "When in doubt, ask.",
            end])
    CLAUDE_MD.write_text(md + "\n")


def detect_key():
    for name in KEY_PREFERENCE:
        k = SSH_DIR / name
        if k.exists() and k.with_suffix(".pub").exists():
            return k
    return None


def main(argv):
    if not argv:
        die(__doc__)
    cmd, args = argv[0], argv[1:]

    if cmd == "list":
        clusters = load_clusters()
        if not clusters:
            print("NO_CLUSTERS")
        for a, c in clusters.items():
            print(f"{a}\t{c['HPC_USER']}@{c['HPC_HOST']}\t{c['HPC_KEY']}")

    elif cmd == "detect-key":
        k = detect_key()
        print(k if k else "NO_KEY")

    elif cmd == "add":
        if len(args) not in (3, 4):
            die("usage: add <alias> <username> <host> [key]")
        alias, user, host = args[:3]
        if not ALIAS_RE.match(alias):
            die(f"invalid alias: {alias}")
        key = Path(args[3]).expanduser() if len(args) == 4 else detect_key()
        if key is None:
            die("no SSH key found; generate one first (see SETUP.md)", 2)
        if not key.exists():
            die(f"key not found: {key}")
        old = load_clusters().get(alias)
        CONF_DIR.mkdir(parents=True, exist_ok=True)
        (CONF_DIR / f"{alias}.conf").write_text(
            f"HPC_USER={user}\nHPC_HOST={host}\nHPC_KEY={key}\n")
        write_ssh_block(alias, user, host, key)
        sync_safeguards(removed=(alias, old["HPC_HOST"]) if old else None)
        print(f"OK: {alias} -> {user}@{host} (key {key})")

    elif cmd == "remove":
        if len(args) != 1:
            die("usage: remove <alias>")
        alias = args[0]
        old = load_clusters().get(alias)
        if not old:
            die(f"cluster not configured: {alias}")
        (CONF_DIR / f"{alias}.conf").unlink()
        write_ssh_block(alias, None, None, None)
        sync_safeguards(removed=(alias, old["HPC_HOST"]))
        print(f"OK: removed {alias}")

    else:
        die(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
