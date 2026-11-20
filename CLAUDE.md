# Rules for agents in this repository

Full rules and the roadmap: `PLAN.md` (section 4: rules for coding agents) and `plans/*.md` (one file per area).
This file is the short list every agent must follow.

## The owner's rules (binding)
- Talk to the owner only in Turkish, briefly. Code, comments, commit messages and plan files are in English.
- Commit only as the owner: `git -c user.name="İdris Avlar" -c user.email="rraeyz@hotmail.com" commit ...`.
  No "Claude" and no Co-Authored-By lines anywhere.
- The product name appears only in `brand.toml`, `README.md` and `packaging/install.sh` (a test enforces it).
- Never touch the owner's GitHub token. Never copy GPL code. MKCLASS is never used. `data/owner/` is read-only.
- Never delete an existing feature without the owner's yes. Do not probe AAVSO with a browser User-Agent.
- Never fabricate data, results, constants or validations. If a format or a method is not written down in the repo
  (plan text, docstrings, code), stop and report instead of guessing.

## Manager and workers (PLAN.md R13)
- The main agent manages: it hands whole plan items to worker subagents with the design decisions taken, reviews,
  tests, commits. It decides open design questions itself (the owner gave full authority); only what needs the
  owner goes into `ISTEKLER.md`. CI is not waited on: work goes on locally, pushes go in batches.

## Subagents (code written for a reviewer)
- Write code only; do not commit or push. Do one plan piece, the smallest complete change.
- Do not stop for design choices: follow the decisions in your prompt; anything else unclear, take the smallest
  option consistent with the plan and name it in your report. Stop only for missing data or a risk to a feature.
- Run tests in one short foreground command each; do not leave background test runs behind.
- Report briefly: files changed, what was done, test results, what was left out and why.

## Environment and checks
- `export PATH=$PWD/.venv/bin:$PATH QT_QPA_PLATFORM=offscreen`
- Lint: `ruff check -q . && ruff format --check -q .`
- Size ratchet: `python tools/module_sizes.py` (limits in `tools/module_sizes_allow.json`; never raise a limit —
  put new code in a small new function or module instead).
- Tests: `python -m pytest -q -p no:cacheprovider -n 2 <files or -k ...>` — at most `-n 2` (memory).
  UI changes also run `tests/test_ui.py tests/test_overflow.py tests/test_layout_fits.py tests/test_kit.py`.
- Every new non-trivial piece of logic gets a test; tests use synthetic data made in the test.

## Code conventions
- Smallest change; reuse existing helpers; no new abstractions or dependencies. Comments only for the why.
- Qt widgets are configured with setters, never constructor keyword arguments. Colours only via `kit/tokens.role()`.
- User-visible strings: `translate = QCoreApplication.translate`, then `translate("Ctx", "…")` (never a `tr=` alias).
- New settings keys are listed in `settings_window` SHOWN or INTERNAL.
- A new step: a title in `engine/titles.py`, its inputs/outputs in `engine/io.py`, then `python tools/api_docs.py`.
- New engine errors need a message template in `ui/messages.py`. A UI action whose engine call can raise
  `ValueError` catches it and shows `translate(e)`; it never crashes.
- Step outputs stay JSON-serialisable (lists and floats, not numpy arrays): the project log stores them as JSON.

## Translations
- `python tools/i18n.py update`, then `python tools/fill_translations.py src/astrowb/resources/i18n/app_tr.ts
  "English=>Türkçe" ...` for each new string; `python tools/i18n.py` must show 0 unfinished for Turkish
  (German/Spanish may stay unfinished); `python tools/translation_review.py glossary` must print 0.
- Glossary: variable star → değişen yıldız, transit → geçiş, eclipse → tutulma, ephemeris → efemer,
  extinction → sönümle.

## Plans
- When a plan piece is done, update its status line in `plans/<area>.md`: **open** / **partial** / **done**,
  with the date, the module/function names and the test name, in the entry's own style.

## Pushing and releasing (main agent only)
- Work on `main`: `git pull -q --rebase origin main && git push -q origin HEAD:main`.
- Each push cancels the previous CI run; never push during a release run.
- Release: bump `__version__` in `src/astrowb/__init__.py`, lint, push, wait for green CI, dispatch `ci.yml`
  with `release=true`, check the 9 release assets, then tell the owner the update command
  (`packaging/install.sh` with `--force`).
