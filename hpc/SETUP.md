# Cluster setup for /hpc

Use this for **first use on a PC** (no clusters configured yet) and for **adding a new cluster** (`/hpc add`).

Follow the steps in order. Report to the user in one line per step. Interactive steps (password, passphrase, OTP) are run **by the user** with the `!` prefix, because you cannot type into an interactive prompt.

In the commands, `<skill>` is this skill's directory (usually `~/.claude/skills/hpc`).

Requirements: Linux, macOS or WSL, with `ssh`, `ssh-keygen`, `python3` and optionally `rsync`, `sshfs` and `tmux`. Check with `command -v ssh ssh-keygen python3 rsync sshfs tmux`. If something is missing, tell the user how to install it (`sudo apt install openssh-client rsync sshfs tmux` or `brew install rsync tmux`) and do not install it yourself without permission.

## 1. Cluster details (always ask)

Always ask the user, even if other clusters are already configured:
- **Username** on the cluster.
- **Host** of the login node (e.g. `login.cluster.example.org`).
- A short **alias** to refer to it, e.g. `cesga` or `lab-cluster`. It must be unique: check with `python3 <skill>/scripts/hpc_config.py list`.
- Whether the cluster uses **2FA/OTP**. This is informational only, because it changes how the connection is opened.

Do not assume any value or copy it from another cluster or another user.

## 2. SSH key

```bash
python3 <skill>/scripts/hpc_config.py detect-key
```
- **If it returns a path:** use that key. Do not ask and do not generate another one. Tell the user in one line.
- **If it returns `NO_KEY`:** a key must be created. Ask the user to run the following (recommend **setting a passphrase**: with multiplexing they type it only once per session):
  ```
  ! ssh-keygen -t ed25519 -a 100 -f ~/.ssh/id_ed25519
  ```
  If the user explicitly asks for a key without a passphrase, you may generate it yourself by adding `-N ""`.
- Use a different key only if the user explicitly asks, passing it as the fourth argument in step 3.
- Check permissions: `chmod 700 ~/.ssh && chmod 600 <key> && chmod 644 <key>.pub`.

## 3. Local configuration

```bash
python3 <skill>/scripts/hpc_config.py add <alias> <username> <host> [private_key_path]
```
The script is idempotent and backs up `~/.ssh/config`. It does the following:
- saves the cluster in `~/.config/claude-hpc/clusters/<alias>.conf`;
- adds a multiplexed `Host <alias>` block to `~/.ssh/config`;
- regenerates the safeguards: `ask` rules in `~/.claude/settings.json` and the rule in `~/.claude/CLAUDE.md`, which prevent connecting to any of the clusters without authorization.

## 4. Install the public key on the cluster

1. **Check whether the key is already installed:**
   ```bash
   ssh -o BatchMode=yes -o ConnectTimeout=10 <alias> true && echo KEY_OK
   ```
   - **If it prints `KEY_OK`:** skip to step 5.
   - **If it asks to confirm the host fingerprint:** run the command below first, which will prompt for it. Remind the user to compare it with the one published by the computing center.
2. **If it is not installed**, installing it needs a password and possibly OTP, so the user runs:
   ```
   ! ssh-copy-id -i <key>.pub <alias>
   ```
   - **Without `ssh-copy-id`**, use the manual alternative:
     ```
     ! cat <key>.pub | ssh <alias> 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
     ```
   - **If the cluster does not accept `authorized_keys`**, some centers require registering the key on a web portal or sending it to support. Show the public key with `cat <key>.pub` and tell the user to register it that way.

## 5. Verification

1. Open the master with `ssh -o BatchMode=yes -fN <alias>`. If it asks for a passphrase or OTP, the user must run `! ssh -fN <alias>`.
2. Check:
   ```bash
   ssh <alias> 'hostname; whoami; command -v sbatch squeue module tmux'
   ```

## 6. Wrap-up

Summarize in 2–3 lines the alias, username, host and key, whether a scheduler is available, and how to use it (`/hpc <alias> <task>`). Then continue with the original task, if there was one.

## Management

- List clusters: `python3 <skill>/scripts/hpc_config.py list`.
- Remove one (ask the user for confirmation first): `python3 <skill>/scripts/hpc_config.py remove <alias>`.
- Reconfigure one: repeat steps 1–5 with the same alias. The script replaces the previous configuration.
