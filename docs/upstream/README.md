# Upstream reviews

The fork's upstream is [chenxiachan/textfold](https://github.com/chenxiachan/textfold).
This directory holds one dated record per review, written by `/upstream`:

    docs/upstream/YYYY-MM-DD.md

The review is read-only until a change is chosen; the record is written even
when nothing is worth taking, so the next review does not re-decide the same
commits.

## What a record contains

- the upstream ref and commit reviewed (`git rev-parse upstream/main`), and the
  date of the previous review it follows;
- the commits, releases or issues that looked relevant, with links or SHAs;
- for each: **take**, **reimplement** or **skip**, and why;
- for a take or reimplement, the port note or `docs/requirements/` file that
  starts the normal workflow, and the upstream commit SHA it came from;
- what was not reviewed, and why.

## The fork's divergences

Check every candidate against these before recommending it:

- the Electron shell is gone; the desktop is MyGo;
- PDFs and pictures go to MinerU's Cloud API only; the local PDF engine is gone;
- the desktop and the Python package are Windows-only;
- the Python package is installed from git, not PyPI;
- the site is this fork's, not the original project's;
- models come from API providers only; there is no product-side agent runtime and no
  subscription aggregation (the ChatGPT local bridge is removed in this round's R0).
  Magpie is an external OpenAI-compatible gateway, not something the product manages;
- reading languages are English and Simplified Chinese only; no new languages and no
  external device/editor integration.

An upstream change that assumes one of these is usually a skip. A change that
is still valuable gets reimplemented against the fork, not merged wholesale.

## Setup

    git remote add upstream https://github.com/chenxiachan/textfold.git
    git fetch upstream --tags

The remote is read-only. Nothing in this fork pushes to it.

## Cadence

Review after an upstream release, or at least monthly. A review that finds
nothing is still a record; the next one starts from its upstream commit.
