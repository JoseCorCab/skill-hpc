---
name: hpc
description: Work on one or more remote HPC clusters (Slurm) from this PC over multiplexed SSH; guided setup on first use. ONLY on explicit user request.
disable-model-invocation: true
argument-hint: "[<alias>] <task> | add | list | remove <alias>"
---

# HPC — remote work over SSH (multi-cluster)

## Authorization rule (mandatory)

- Use this skill only when the user explicitly invokes it (`/hpc`) or expressly asks to work on a cluster in this session.
- Never connect to a cluster on your own initiative, in auto mode, or because a task "seems" to need it. If you think it is needed, ask first.
- Authorization covers only the current session and only the cluster named. It does not carry over between sessions or between clusters.

## Step 0 — Configured clusters

`<skill>` is this skill's directory (usually `~/.claude/skills/hpc`).

```bash
python3 <skill>/scripts/hpc_config.py list
```
- **If it prints `NO_CLUSTERS`** (first use on this PC): read `SETUP.md` and run the full setup. Always ask which cluster.
- **If the argument is `add`:** read `SETUP.md` and add a new cluster.
- **If the argument is `list` or `remove <alias>`:** use the script (ask for confirmation before `remove`) and stop.
- **Otherwise**, pick the working cluster:
  - if the argument starts with a configured alias, use that one;
  - if only one cluster is configured, use that one;
  - if there are several and it is unclear which, ask. Do not choose on your own.

In this document, `<alias>` is the SSH alias of the chosen cluster. When working with several clusters in the same session, always state which cluster each command targets.

## Connection

- The connection is multiplexed (`ControlMaster`): there is one authenticated socket per cluster and every command reuses it.
- Before working, check the master:
  ```bash
  ssh -O check <alias> 2>&1
  ```
  If it is not running, try `ssh -o BatchMode=yes -fN <alias>`. If that fails because it needs a passphrase, password or OTP, ask the user to run `! ssh -fN <alias>` and wait.
- Never run `ssh` loops or rapid retries. If a connection fails, stop and report.

## Execution

- Each call is independent: `cd`, `module load`, `conda activate` and environment variables do not persist. Chain everything in a single command:
  ```bash
  ssh <alias> 'cd ~/project && module load R && Rscript script.R'
  ```
- Use single quotes so variables (`$USER`, `$HOME`) expand on the cluster, not locally.
- Batch several queries into one call instead of making many small ones.
- **No heavy computation on the login node.** Anything non-trivial (more than a few seconds of CPU, or significant RAM/IO) goes through the scheduler: `sbatch`, or `srun` for short tasks.
- Modules, partitions and paths differ between clusters. Look them up on each one (`module avail`, `sinfo`) instead of assuming.
- For long-running or interactive processes, use `tmux` on the cluster: `ssh <alias> 'tmux new -d -s name "command"'`. Check on it later with `tmux capture-pane -pt name`.
- Monitor jobs with `squeue -u $USER`, `sacct -j <id>` and `tail` on the logs. No aggressive polling: leave minutes between checks.

## Editing files

Choose one of these two options:

1. **sshfs** (convenient; lets you use Read/Edit/Write directly):
   ```bash
   mkdir -p ~/hpc_mnt/<alias> && sshfs <alias>: ~/hpc_mnt/<alias> -o reconnect,ServerAliveInterval=60
   # unmount: fusermount -u ~/hpc_mnt/<alias>   (macOS: umount ~/hpc_mnt/<alias>)
   ```
   Do not read huge files (BAM, FASTQ, matrices) through the mount. Inspect them with `ssh <alias> 'head ...'`.
2. **Edit locally and sync**:
   ```bash
   rsync -avz --exclude '.git' ./ <alias>:~/project/
   ```
   Before any `rsync` with `--delete`, always do a `--dry-run` and confirm with the user.

To copy data between two clusters, go through the local machine with `rsync` unless the user says otherwise. Report the transfer size first.

## Safety

- Do not delete or overwrite data on the cluster (`rm`, `rsync --delete`, `>` onto existing files) without explicit confirmation.
- Do not `scancel` jobs you did not submit in this session without asking.
- Do not transfer sensitive or patient data to the local PC unless the user explicitly asks.
- Never read, display or copy private keys (`~/.ssh/id_*` without `.pub`).

## Wrap-up

When finished, if the user asks: `fusermount -u ~/hpc_mnt/<alias>` (if mounted) and `ssh -O exit <alias>`.

## Requested task

$ARGUMENTS
