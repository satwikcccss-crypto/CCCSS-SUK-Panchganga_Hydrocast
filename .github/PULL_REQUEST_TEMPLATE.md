## 📋 Summary

<!-- Ek line mein batayein: yeh PR kya karta hai? -->



## 🔗 Related Issue(s)

<!-- Closes #<issue_number> ya Fixes #<issue_number> -->
Closes #

---

## 🧩 Type of Change

<!-- Jo applicable ho usse ✅ karein -->

- [ ] 🐛 Bug fix (non-breaking change)
- [ ] ✨ New feature (non-breaking change)
- [ ] 💥 Breaking change (existing functionality affected)
- [ ] 🔧 Refactor / Code cleanup (no functional change)
- [ ] 📊 Data / Model update (hydrologic params, rating curves, thresholds)
- [ ] 📝 Documentation update
- [ ] 🔒 Security fix
- [ ] ⚙️ CI/CD / DevOps change

---

## 🌊 Hydrologic Impact Assessment

<!-- Kya is change se forecast accuracy, alert thresholds, ya physics model affect hota hai? -->

- [ ] No hydrologic impact (UI/infra only)
- [ ] Hydrologic model affected → explain below:

<!-- Agar model affected hai to briefly explain: -->



---

## 🧪 Testing

### Tests Run

```bash
# Commands jo run kiye
pytest tests/ -v
ruff check .
ruff format . --check
```

### Test Results

<!-- Pass/fail summary paste karein -->

```
# Example:
# 286 passed, 0 failed, 0 warnings
```

### New Tests Added?

- [ ] Yes — new test cases add kiye (describe below)
- [ ] No — kyun? (explain below)

<!-- Describe new tests OR explain why no tests: -->



---

## 📸 Screenshots / Demo (UI changes ke liye)

<!-- Frontend changes hain to before/after screenshots ya screen recording attach karein -->

| Before | After |
|--------|-------|
| _(screenshot)_ | _(screenshot)_ |

---

## 📝 Changelog Entry

<!-- CHANGELOG.md ke `[Unreleased]` section mein kya add kiya? Copy-paste karein: -->

```markdown
### Added / Fixed / Changed
- ...
```

---

## ✅ PR Checklist

<!-- Merge se pehle sabhi items check karein -->

**Code Quality**
- [ ] `ruff check .` — zero linting errors
- [ ] `ruff format . --check` — code properly formatted hai
- [ ] Type hints added/updated jahan zaroorat thi

**Testing**
- [ ] `pytest tests/ -v` — sab tests pass hain (286+ suite)
- [ ] New functionality ke liye tests likhe hain
- [ ] Edge cases aur error paths cover hain

**Documentation**
- [ ] Docstrings updated hain (functions/classes)
- [ ] `CHANGELOG.md` update kiya hai `[Unreleased]` section mein
- [ ] README / ARCHITECTURE update kiya hai (agar relevant ho)
- [ ] `python -m mkdocs build --strict` — zero warnings

**General**
- [ ] PR ek logical change pe focused hai (mega-PR nahi hai)
- [ ] Breaking changes clearly documented hain
- [ ] Sensitive data (keys, passwords, PII) commit mein nahi hai
- [ ] Self-review kiya hai apne code ka

---

## 🗒️ Additional Notes for Reviewer

<!-- Koi bhi context jo reviewer ko help kare — design decisions, known limitations, follow-up issues, etc. -->


