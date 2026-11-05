---
title: Alerts & Delivery Reference
---

# Alerts & Delivery Reference

Threshold evaluation, de-duplication, and the Telegram flood bulletin.

---

## Alert evaluation and de-duplication


!!! tip "Priority ordering, not lexicographic"
    An earlier query compared `alert_type >= %s` **as text**. Because
    `'watch' > 'warning' > 'emergency'` alphabetically, that expression silently
    inverted the severity order and let a de-escalation overwrite an escalation.
    The `CASE` expression above ranks severity explicitly and compares the
    integers, so a *downgrade* is correctly allowed to supersede a stale
    escalation while a *repeat* of the same level is suppressed.

---

## Telegram bulletin


`get_severity_badge()` accepts either the CWC threshold vocabulary
(`ALERT` / `WARNING` / `DANGER` / `HFL_EXCEEDED`) or the database `alert_type`
vocabulary (`watch` / `warning` / `emergency`) and maps both onto the same badge,
so a bulletin rendered from either source is visually identical.

---

## Alert classification and de-duplication

`classify_alert(stage_m, site_id)` maps the converted stage onto the WRD ladder for
the site. At the Shivaji Bridge reference section the thresholds are:

| Stage at Shivaji (m MSL) | Level | WRD reference |
|:---|:---|:---|
| ≥ 545.33 | `HFL_EXCEEDED` | 1,969 m³/s historical peak |
| ≥ 543.30 | `DANGER` | 2,675 m³/s danger mark |
| ≥ 542.70 | `WARNING` | 1,800 m³/s warning mark |
| below 542.70 | `ALERT` / normal | below the warning band |

The CWC level is then translated to the alert vocabulary the notifier understands
(`watch`, `warning`, `emergency`) by `_cwc_to_alert_type()`.

Before an alert is written, the router selects the existing active alert for the
site ordered by severity — `emergency (3) > warning (2) > watch (1)` — then by
`issued_at` descending. If the existing alert's priority is greater than or equal
to the incoming one, the insert is skipped and the duplicate is suppressed. This
is what prevents a rising river from generating one bulletin per hourly cycle.

The Telegram bulletin itself is formatted by `format_telegram_alert()` and carries
the site, stage, trend, margin above the warning mark, the three WRD reference
datums, and the recommended action line. Delivery uses webhook mode when
`get_webhook_urls()` returns any URL, and falls back to `start_polling()`
otherwise.


## `src/alerts/evaluator.py`

::: src.alerts.evaluator

---

## `src/alerts/telegram_bot.py`

::: src.alerts.telegram_bot
