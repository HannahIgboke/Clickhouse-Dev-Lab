# Publish ClickHouse Dev Lab (the ₦0 path)

This gets you the thing you asked for: **a link someone clicks that opens a real
`clickhouse-client` in the browser.** It costs nothing. The practice runs on the *visitor's*
free GitHub Codespaces hours, not on a server you pay for.

Do these once. It takes about 10 minutes plus a few minutes of GitHub Actions running.

---

## 1. Put the code on GitHub

If you have not already:

1. Create an empty repository at <https://github.com/new>.
   - Name: `clickhouse-dev-lab` (or anything).
   - **Public** (Pages and free Codespaces names are simplest for public repos).
   - Do **not** add a README or .gitignore — the repo already has them.
2. Copy its URL (e.g. `https://github.com/YOUR-USERNAME/clickhouse-dev-lab.git`).
3. In this folder, run:

```bash
git add -A
git commit -m "One-click Codespaces practice + website CTAs"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/clickhouse-dev-lab.git
git push -u origin main
```

Replace `YOUR-USERNAME` everywhere. If `git remote add` says it already exists, use
`git remote set-url origin <url>` instead.

## 2. Make the Codespaces link work

Nothing to configure — the button `https://codespaces.new/YOUR-USERNAME/clickhouse-dev-lab`
works as soon as the repo exists. When someone clicks it:

- GitHub creates a Codespace from `.devcontainer/devcontainer.json`,
- installs the package (`pip install -e .`),
- runs `.devcontainer/welcome.sh`, which starts ClickHouse and prints what to type next,
- opens `docs/START-HERE.md`.

**Test it yourself once** by visiting that URL. The first boot takes a minute or two while
Docker images download. You should see the ClickHouse Dev Lab banner and a working `chlab`.

### Optional: make it faster with a prebuild

Prebuilds cut first-boot time from minutes to seconds, but they consume your Codespaces
storage quota. For a personal/community project you can skip this. If you want it:
GitHub → your repo → **Settings → Codespaces → Prebuild configuration → Set up prebuild**,
branch `main`, keep the default devcontainer. Change your mind any time.

## 3. Turn on the website (GitHub Pages)

The site is generated from the task files by `.github/workflows/pages.yml`, which is already in
the repo and runs on every push to `main` — you just have to switch Pages on once:

1. Repo → **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. Wait for the “website” action to finish (Actions tab). Your site is then at
   `https://YOUR-USERNAME.github.io/clickhouse-dev-lab/`.

The page shows the task catalogue, the objective coverage table, and the **“Open in a browser
(one click, free)”** button that points at Codespaces.

> The generated links use the `GITHUB_REPOSITORY` that Actions provides, so you do not need to
> edit any URL by hand. If you build the site locally, set that variable first:
> `GITHUB_REPOSITORY=YOUR-USERNAME/clickhouse-dev-lab python -m chlab.cli site --out site`

## 4. Replace the placeholder name in the README

The README ships with `YOUR-USERNAME` in three places (the Codespaces badge, the website badge,
and the `git clone` line). Once you know your username, replace them so the badges render.
(Leaving them will show broken badges, not a broken site.)

## 5. Tell people where to click

Share the Pages link, not the raw repo:
`https://YOUR-USERNAME.github.io/clickhouse-dev-lab/`

That page is the “come and practise” front door: catalogue, coverage, and the one-click button.

---

## What this costs

- **Hosting:** ₦0. Pages is free for public repos.
- **Practice runs:** ₦0 to you — each visitor’s Codespace draws on their own GitHub free
  monthly allowance (about 60 hours on the 2-core machine). Your repo is just the recipe.
- **CI:** GitHub Actions on public repos is free within the monthly minutes allowance; the two
  workflows here are small.

## The one thing that can bite you

**Codespaces free hours are per-user and per-month.** A keen user can exhaust them. On the page
and in `docs/START-HERE.md` we tell people to **stop their Codespace when they finish**. If you
ever hit limits or want true anonymous, disposable sessions with no GitHub login at all, that is
“Phase 2” in [PLAN.md](PLAN.md) — a container per session — and it is the point at which you
would need a small budget. Until then, Phase 1 is the right call.

## Troubleshooting

- **The Codespace opens but ClickHouse is not up yet.** Wait ~30 s, then run `chlab up` in the
  terminal. `welcome.sh` logs to `/tmp/chlab-up.log` if you want to look.
- **`chlab: command not found`.** Run `pip install -e .` once, or use `python -m chlab.cli`.
- **The Pages action failed.** Confirm Pages Source is set to “GitHub Actions” (step 3) and that
  the action has `pages: write` permission (it does, in the workflow).
- **A task will not grade.** Run `chlab reset <n>` then `chlab start <n>` to rebuild its data.