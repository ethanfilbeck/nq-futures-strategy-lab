# Publishing to GitHub safely

Run these in **PowerShell 7** inside `Documents\nq_bot`.

## 0. Before anything

- [ ] **Regenerate the Databento key** in the Databento portal (delete the old one), and paste the new key into `.env`.
      The old key appeared in a chat transcript, so treat it as exposed.
- [ ] Delete the `_to_delete` folder.

## 1. Install Git and the GitHub CLI (once)

```
winget install -e --id Git.Git
winget install -e --id GitHub.cli
```
Close and reopen PowerShell 7, then sign in:
```
gh auth login
```
(choose GitHub.com → HTTPS → log in with a web browser).

## 2. Keep your email private in commits

GitHub → Settings → Emails → tick **Keep my email addresses private**, and copy the `…@users.noreply.github.com` address it shows. Then:
```
git config --global user.name "Ethan Filbeck"
git config --global user.email "<that noreply address>"
```

## 3. Create the repository locally and check it

```
git init
git add .
git status
py scripts/prepublish_check.py
```
`git status` must **not** list `.env`, `data/`, `logs/`, `_to_delete/` or any `runs/...csv`.
The check must print `OK: … nothing secret or licensed found`. If it prints **DO NOT PUSH**, fix what it lists
(`git rm --cached <file>`) and run it again.

## 4. Commit and publish

```
git commit -m "MNQ strategy lab: research results (all strategies failed), risk engine, IB paper adapter"
gh repo create nq-futures-strategy-lab --public --source . --push
```

## 5. After publishing

- Open the repo page and confirm `.env` and `data/` are not there.
- Add a short description: *"Futures research system that rejected 3 strategies on 6 years of MNQ data — pre-registration, walk-forward, risk engine, IB paper adapter."*
- Pin it on your GitHub profile.

If a secret is ever pushed by mistake: revoke/regenerate it immediately (deleting the file is not enough — it stays in git history).
