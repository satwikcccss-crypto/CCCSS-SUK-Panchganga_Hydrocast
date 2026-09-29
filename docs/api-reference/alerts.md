---
title: Alerts & Delivery Reference
---

# Alerts & Delivery Reference

Threshold evaluation, de-duplication, and the Telegram flood bulletin.

---

## Alert evaluation and de-duplication

```text
  peak stage at each bridge site
            │
            ▼
  classify_alert(stage_m, site_id)
      ├── stage ≥ 545.33 m  → HFL_EXCEEDED   (1 969 m³/s historical peak)
      ├── stage ≥ 543.30 m  → DANGER         (2 675 m³/s danger mark)
      ├── stage ≥ 542.70 m  → WARNING        (1 800 m³/s warning mark)
      └── otherwise         → ALERT / normal
            │
            ▼
  _cwc_to_alert_type(level)  ──►  watch | warning | emergency
            │
            ▼
  ┌────────────────────────────────────────────────────────────┐
  │  SELECT existing active alert for this site,               │
  │         ordered by  emergency(3) > warning(2) > watch(1)  │
  │         then issued_at DESC                                │
  └───────────────────────────┬────────────────────────────────┘
                              │
        existing.priority ≥ new.priority ──► SKIP (duplicate suppressed)
                              │
                             no
                              ▼
                     INSERT new alert_events row
```

!!! tip "Priority ordering, not lexicographic"
    An earlier query compared `alert_type >= %s` **as text**. Because
    `'watch' > 'warning' > 'emergency'` alphabetically, that expression silently
    inverted the severity order and let a de-escalation overwrite an escalation.
    The `CASE` expression above ranks severity explicitly and compares the
    integers, so a *downgrade* is correctly allowed to supersede a stale
    escalation while a *repeat* of the same level is suppressed.

---

## Telegram bulletin

```text
   forecast cycle completes
            │
            ▼
  ┌─────────────────────────────────────────────────────────┐
  │  format_telegram_alert()                                │
  │                                                         │
  │   🌊 HYDROCAST FLOOD BULLETIN 🌊                        │
  │   Authority: Centre for Climate Change & Sustainability  │
  │              Studies, Shivaji University Kolhapur        │
  │   Classification: 🟠 [WARNING / ADVISORY]               │
  │   ─────────────────────────────                         │
  │   Site / stage / trend / margin above warning mark      │
  │   WRD reference datums: Warning · Danger · HFL          │
  │   Recommended action line                                │
  └───────────────────────────┬─────────────────────────────┘
                              │
                              ▼
  build_telegram_application()
     ├── get_webhook_urls()  non-empty ──► run webhook mode
     └── otherwise           empty     ──► start_polling()
```

`get_severity_badge()` accepts either the CWC threshold vocabulary
(`ALERT` / `WARNING` / `DANGER` / `HFL_EXCEEDED`) or the database `alert_type`
vocabulary (`watch` / `warning` / `emergency`) and maps both onto the same badge,
so a bulletin rendered from either source is visually identical.

---

## `src/alerts/evaluator.py`

::: src.alerts.evaluator

---

## `src/alerts/telegram_bot.py`

::: src.alerts.telegram_bot
