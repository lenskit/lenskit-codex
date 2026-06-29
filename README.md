# LensKit Codex

This repository contains the LensKit Codex, a repository of recommender system
evaluation and tuning results.

## Software Dependencies

The Python dependencies for *running* the Codex experiments are managed with
[uv][]. The other dependencies for working on the Codex are managed with
[Mise][], and Mise can also install `uv`.

To install Mise, see [the instructions][install-mise].  If you want to install Mise
on a Linux machine and have it automatically self-activate in your Bash profile, you can
run:

```console
$ curl https://mise.run/bash
```

## Local Setup

To set up an environment to work on the Codex, first clone the repository with
either `git` or `gh`.  Then:

1. Trust the workspace with `mise trust .`
2. Install Mise dependencies with `mise install`
3. Install Python dependencies with `uv sync`

If you set up Mise to auto-activate in your shell, then whenever you `cd` into
the directory, it will automatically add the various dependencies and the Python
virtual environment to your shell environment.  If you don't want auto-activation,
you can spawn a subshell with the environment with:

```console
$ mise x -- bash
```

Finally, create a file `lenskit.local.toml` with any configuration needed for
your local machine or environment. If you are working on one of the INERTIAL
computers, this should usually contain at least a `machine` setting,
corresponding to one of the defined machines in `lenskit.toml`, e.g.:

```toml
machine = "screamer"
```

### DVC Access

If you are part of [INERTIAL][], or otherwise have access to our asset
repository, add your credentials to your **local** configuration:

```console
$ dvc remote modify --local vault user=<user> password=<passwd>
```

[uv]: https://docs.astral.sh/uv/
[Mise]: https://mise.jdx.dev
[install-mise]: https://mise.jdx.dev/installing-mise.html
[INERTIAL]: https://inertial.science
