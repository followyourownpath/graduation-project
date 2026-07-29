# GitHub CI Guide

The repository uses GitHub Actions for automated checks and protects the `main` branch.
Do not push directly to `main`; submit every change through a pull request (PR).

---

## 1. Available Checks

GitHub runs these checks whenever a PR is opened or receives a new commit:

| Name in Actions | Required check name | Purpose |
|-----------------|---------------------|---------|
| Conflict Check | `check-conflict` | Checks for conflicts with `main` and unresolved markers such as `<<<<<<<` |
| Frontend CI | `build` | Installs frontend dependencies, runs lint, and builds the application |
| Backend CI | `check` | Installs backend dependencies and validates Python syntax |

All three checks must pass before a PR can be merged into `main`.

Workflow files:

```text
.github/workflows/
  conflict-check.yml
  frontend.yml
  backend.yml
```

---

## 2. Standard Development Workflow

```bash
# 1. Update local main
git checkout main
git pull origin main

# 2. Create a feature branch from the latest main
git checkout -b feature/your-feature

# 3. Make and submit the change
git add .
git commit -m "feat: describe the change briefly"
git push -u origin feature/your-feature
```

Then, on GitHub:

1. Open the repository and select **Compare & pull request**, or choose **Pull requests → New**.
2. Set the **base** branch to `main` and the **compare** branch to your feature branch.
3. Create the PR and wait approximately one or two minutes for Actions to finish.
4. When all checks pass, select **Merge pull request**.

---

## 3. Viewing Check Results

- The bottom of the PR page shows the status of every check.
- The repository's **Actions** tab contains full run details and logs.

A green check means success. A red cross means failure; open the failed check to inspect the error.

---

## 4. Resolving Failures

### Conflict Check Fails

The branch conflicts with `main`. Resolve it locally:

```bash
git checkout your-branch
git fetch origin
git merge origin/main
# Resolve conflicts in the editor, then:
git add .
git commit -m "chore: resolve merge conflicts with main"
git push
```

Do not leave Git conflict markers in the resolved files. Search for runs of seven less-than,
equals, or greater-than characters and confirm that none remain.

### Frontend CI Fails

The failure is usually caused by lint or build errors. Reproduce it locally:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

Fix the error, commit, and push. The PR checks will rerun automatically.

### Backend CI Fails

Reproduce the check locally:

```bash
cd backend
pip install -r requirements.txt
python -m compileall .
```

Fix the error and push the new commit.

---

## 5. Team Guidelines

1. Never run `git push origin main`; branch protection should reject it.
2. Update from `origin/main` before starting work to reduce conflicts.
3. Run `npm run lint` and `npm run build` before submitting frontend changes.
4. Never commit `.env` files, secrets, or model weights.
5. Keep each PR focused on one concern so it remains easy to review and diagnose.

---

## 6. Dependabot

Actions may also show automated **Dependency Graph** or Dependabot jobs. These are dependency
scans rather than the required CI checks described above. For routine development, focus on the
three required checks.

If a check fails, consult its Actions log or contact the teammate responsible for CI.
