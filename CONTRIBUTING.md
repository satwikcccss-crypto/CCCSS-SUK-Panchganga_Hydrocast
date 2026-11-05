# Contributing to HydroCast

Thank you for your interest in contributing to **HydroCast**! We welcome contributions from hydrologists, data scientists, software engineers, civil authorities, and civic hackers dedicated to open science and disaster resilience.

---

## Code of Conduct

By participating in this project, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md). Please report any unacceptable behavior to **`satwikcccss@gmail.com`**.

---

## How Can I Contribute?

* **Reporting Bugs:** Submit a GitHub Issue with full traceback, environment details, and expected vs. actual behavior.
* **Suggesting Features:** Propose hydrologic routing enhancements, new sensor drivers, or UI improvements via GitHub Discussions or Issues.
* **Improving Documentation:** Clarify docstrings, fix typos, or enhance the interactive Archify consoles in [`docs/`](docs/).
* **Submitting Pull Requests:** Implement bug fixes or new features following our test-driven development workflow.

---

## Local Development Workflow

### 1. Fork & Clone
```bash
git clone https://github.com/<your-username>/CCCSS-SUK-Panchganga_Hydrocast.git
cd CCCSS-SUK-Panchganga_Hydrocast
git checkout -b feature/my-enhancement
```

### 2. Python Backend Setup
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.lock
pip install -r requirements-dev.txt
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## Testing & Quality Gates

Every pull request must satisfy our strict CI/CD gates before merging:

1. **Python Test Suite:**
   ```bash
   pytest tests -v
   ```
   All unit, physics, and security tests must pass (286+ tests).

2. **Code Linting & Formatting:**
   ```bash
   ruff check .
   ruff format .
   ```

3. **Strict Documentation Build:**
   ```bash
   python -m mkdocs build --strict
   ```
   MkDocs must build with zero warnings and zero broken links.

4. **Frontend TypeScript & Build Verification:**
   ```bash
   cd frontend
   npm run build
   ```

---

## Pull Request Guidelines

1. Ensure all tests and linting pass locally before opening a PR.
2. Link your PR to any relevant open issues (`Closes #123`).
3. Keep PRs focused on a single logical change; avoid mega-PRs mixing unrelated features.
4. Update [`CHANGELOG.md`](CHANGELOG.md) under the `[Unreleased]` section.
5. Project maintainers will review your PR and provide constructive feedback.

Thank you for helping protect the lives, livelihoods, and civic resilience of the Panchganga Basin!
