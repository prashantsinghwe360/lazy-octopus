# lazy-octopus · sample data for the We360 executive dashboard

Six months (**1 April – 30 September 2026**) of realistic, **entirely made-up** workforce data, shaped the way a We360 export looks. It exists so the executive dashboard can be judged on data that behaves like a real client, not on a handful of hand-typed numbers.

Names, emails and IDs are invented. Team structure and the overall shape are calibrated to a real client review deck:

| Check | Deck | This data |
|---|---|---|
| Directory users | 462 | 462 (+5 test accounts) |
| Presence coverage (present ÷ working days) | ~76% | ~80% |
| Online time per present day | ~7.4h | ~7.4h |
| Active time per present day | ~3.2h | ~3.2h |
| People averaging under 2h active, present 50+ days | 67 | ~72 |
| People using any AI tool | 82% | ~87% |
| Non-work share of active time | 0.36% | ~0.4% |

## What's in it

`data/` holds the tables, one CSV per export. `derived/` holds the same data reshaped for the dashboard; `generate.py` rebuilds both deterministically (fixed seed).

| File | One row per | Key columns |
|---|---|---|
| `data/users.csv` | Directory account | `user_id`, `employee_id`, `name`, `email`, `team`, `department`, `location`, `account_type` (user / test), `join_date`, `exit_date`, `status` |
| `data/teams.csv` | Team | `team`, `department`, `client_facing`, `headcount` |
| `data/daily_activity.csv` | Person × working day | `date`, `attendance` (Present / Half day / Leave / Absent), `leave_type`, `punch_in`, `punch_out`, `working_h`, `online_h`, `active_h`, `idle_h`, `break_h`, `offline_h`, `productive_h`, `unproductive_h`, `neutral_h` |
| `data/leaves.csv` | Leave request | `leave_type`, `start_date`, `end_date`, `days`, `status` |
| `data/holidays.csv` | Public holiday | `date`, `holiday`, `country` |
| `data/app_usage_monthly.csv` | Person × month × app/URL | `item`, `kind` (app / url), `category`, `classification` (for that person's team), `hours`, `active_days` |
| `data/ai_usage_monthly.csv` | Person × month × AI tool | `tool`, `hours`, `sessions` |
| `data/category_mapping.csv` | Team × category | `classification` (productive / neutral / unproductive) |
| `data/settings.csv` | Setting | Half day, wellness, goals, capacity benchmark, meeting tracking |
| `data/score_weights.csv` | Score metric | `weight`, `enabled` |

### How the numbers fit together

Every daily row follows the product's nesting, so totals always reconcile:

- **Working = Online + Break + Offline**
- **Online = Active + Idle**
- **Active = Productive + Unproductive + Neutral**

Unproductive hours on a day are the sum of that person's unproductive apps and URLs, so `app_usage_monthly` and `daily_activity` agree.

### Realistic behaviour built in

| Pattern | Where you'll see it |
|---|---|
| Absence ≠ leave | ~6% of working days are approved leave (`leaves.csv`); a further share are **Absent** with no signal, mostly from ~10% of people whose agent is often not running. This is what drives the coverage gap. |
| Long leave | Two people on 60-day maternity leave. |
| Joiners and leavers | ~7% join during the period, ~4.5% leave (`join_date`, `exit_date`). |
| Week rhythm | Fridays ~6% lighter, Mondays slightly heavier. |
| Month-end close | Finance & Compliance works ~18% longer in the last days of each month. |
| Project crunch | Salesforce Practice runs ~8% longer in July. |
| Public holidays | Seven Malaysian holidays are excluded from working days. |
| Off-screen roles | Sales, Marketing and GCC Presales show low active time (calls, client visits). |
| Mis-tagged work tools | The live Salesforce org (`client-lex.lightning.force.com`) sits in a non-work category while its sandbox is in CRM; Zoho Books and HSBCnet are mapped unproductive for Finance. |
| Non-work outliers | One heavy gamer, a few heavy video users, a handful of adult-site hits and one trace of gambling. |
| AI adoption | Broad but shallow: most people open Microsoft 365 Copilot, a minority use ChatGPT / Claude / Gemini, and ~3% are power users. |
| Data quality | Three employee IDs appear under two identities; five test/admin accounts. |

## How the dashboard calculates things

- **Per present day:** every average divides by days with a punch or online signal only.
- **Capacity:** benchmark 7h of online time (settings), healthy zone 6.25h–7.75h (±11%).
  - Net Ideal Capacity = 7h × working days × headcount.
  - Net Achieved Capacity = total online time.
  - Gap = achieved − ideal = −absence − shortfall + extra.
- **Red flag:** score (from `score_weights.csv`) under 50 of 100, two or more problems, and present on 38%+ of working days.

## Regenerate

```bash
python generate.py
```

Python 3.9+, no dependencies. Change `random.seed(2026)` for a different but equally realistic sample.
