# skill-hpc

A [Claude Code](https://claude.com/claude-code) skill for working on one or more HPC clusters from your PC.

It lets you run Claude Code on your local machine while it edits files and runs commands on HPC clusters (Slurm) over SSH.

## Features

- **One SSH connection per cluster.** It uses multiplexing (`ControlMaster`): you authenticate once (passphrase or OTP) and every Claude command reuses that socket. The cluster sees no burst of connections or repeated logins, so fail2ban is not triggered and 2FA is not requested on every command.
- **Multiple clusters.** Each cluster has its own alias (`/hpc <alias> <task>`), and you can add or remove clusters as needed.
- **Self-configuring.** The first `/hpc` on a PC starts a guided setup. Claude asks for the cluster's username, host and alias, reuses your existing SSH key if there is one (otherwise helps you create it), installs it on the cluster and verifies the connection.
- **On demand only.** The skill never triggers by itself (`disable-model-invocation: true`). The setup also adds two safeguards so that no session, not even in auto mode, connects to a cluster unless you ask:
  - `ask` rules in `~/.claude/settings.json`, which require confirmation before any `ssh`, `rsync`, `scp` or `sshfs` to the configured clusters;
  - a rule in `~/.claude/CLAUDE.md` that forbids connecting without explicit authorization.
- **HPC good practices.** No computation on the login node (everything goes through `sbatch`/`srun`), `tmux` for long-running processes, no aggressive polling, and confirmation before deleting data or cancelling jobs.

## Requirements

- Linux, macOS or WSL2.
- `ssh`, `ssh-keygen` and `python3`.
- Optional: `rsync`, `sshfs` (to mount the cluster home) and `tmux`.

On Debian/Ubuntu/WSL:
```bash
sudo apt install openssh-client rsync sshfs tmux
```

## Installation

The skill is **copied** (not symlinked) into Claude's skills folder:

```bash
git clone https://github.com/JoseCorCab/skill-hpc.git
mkdir -p ~/.claude/skills
cp -r skill-hpc/hpc ~/.claude/skills/
```

Then open Claude Code and type `/hpc`. On first use it configures itself.

To **update**, run `git pull` in the repo and copy it again:
```bash
cp -r skill-hpc/hpc ~/.claude/skills/
```
Your cluster configuration lives in `~/.config/claude-hpc/` and is kept across updates.

## Usage

```text
/hpc                                   # first time: guided setup
/hpc add                               # add another cluster
/hpc list                              # show configured clusters
/hpc remove <alias>                    # remove a cluster
! ssh -fN <alias>                      # open the connection (passphrase/OTP once)
/hpc <alias> run the pipeline in ~/project with sbatch
/hpc <alias> check my jobs and the log of the latest one
```

With a single cluster configured, the alias is optional. With several, if you don't name one, Claude asks which to use.

Commands that need a password, passphrase or OTP are run by you with the `!` prefix, because Claude cannot type into interactive prompts.

To close the connection: `ssh -O exit <alias>`.

## What it changes on your system

| File | Change |
|---|---|
| `~/.config/claude-hpc/clusters/<alias>.conf` | Username, host and key path for each cluster |
| `~/.ssh/config` | One `Host <alias>` block per cluster between `# >>> claude-hpc:<alias> >>>` markers (backup saved as `config.bak.<date>`) |
| `~/.claude/settings.json` | `permissions.ask` rules for ssh/rsync/scp/sshfs to the clusters |
| `~/.claude/CLAUDE.md` | "Do not connect without authorization" rule between markers |

Reconfiguring an alias replaces its configuration without duplicating it, and `/hpc remove <alias>` cleans it out of all those files.

## Layout

```
hpc/
├── SKILL.md               # remote work instructions
├── SETUP.md               # guided setup / add cluster
└── scripts/hpc_config.py  # add | remove | list | detect-key (idempotent)
```

## Can I get banned for this?

Unlikely with this setup: the cluster sees a single SSH session, just like a normal user. What usually causes trouble is running computation on the login node, which the skill forbids. Still, check each center's acceptable use policy: some explicitly forbid automated access.
