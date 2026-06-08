# Timezone handling

> All charts, tables, and report figures use **Europe/Rome (UTC+2 in June)** as
> the display timezone. This file documents how we got there, why, and what to
> do if a future contributor downloads new CloudWatch data.

---

## The problem we hit

Each teammate downloaded their CloudWatch CSVs from a different machine, and
the AWS Console default ("Local timezone") means the CSV uses **whatever
timezone the downloader's browser/OS is set to**. Result:

| Lambda | Downloaded by | Detected offset | Why |
|---|---|---|---|
| `resize-fn` | Nico (laptop set to Italian time) | UTC+2 (Rome) | AWS default + Italian system tz |
| `grayscale-fn` | Prajwal (laptop in Rome) | UTC+2 (Rome) | Same |
| `edge-fn` | Mathias | UTC | Manually selected "UTC" in the AWS Console |

Locust, on the other hand, always emits **UTC epoch seconds** in
`*_stats_history.csv` (column `Timestamp`). It's unambiguous.

So we had three different time references mixed together: two CSVs in Rome
time, one CSV in UTC, and the load-test driver in UTC. Matching scenarios with
their server-side CloudWatch data needs them in the same timezone — otherwise
the script tries to find Lambda activity in a window that doesn't overlap with
when the test actually ran, and produces empty results (which is what
originally happened to `resize-fn`).

---

## The convention

1. **Single source of truth for ground truth**: the Locust UTC epoch.
2. **Detection**: for each CloudWatch CSV, find the busiest minute (peak of
   `<op>_invocations.csv`) and compare it with the midpoint of the Locust
   scenarios for that operation. The integer-hour difference is the CSV's
   offset from UTC.
3. **Display**: all timestamps (Locust epochs and CW samples) are converted to
   `Europe/Rome` before plotting or being written to summary tables. Rome time
   is what the team and the readers of the report intuitively understand.

The detection + conversion live in `analysis/_tz_helper.py` and are used by:

- `analysis/cloudwatch/analyze_cloudwatch.py`
- `analysis/cross_reference/compare_locust_vs_cloudwatch.py`

Both scripts log the detected offset at startup, e.g.

```
[resize]    CSV detected as UTC+2 -> displayed in Europe/Rome
[grayscale] CSV detected as UTC+2 -> displayed in Europe/Rome
[edge]      CSV detected as UTC0 -> displayed in Europe/Rome
```

If a CSV's detected offset is something unexpected (e.g. `UTC-5`), check
whether the downloader's machine timezone was unusual or whether the wrong
window was selected in the AWS Console.

---

## For future contributors downloading new CSVs

You **don't** have to manually convert anything. The scripts auto-detect. Just:

1. Drop the 5 CSVs (`<op>_invocations.csv`, `<op>_duration.csv`,
   `<op>_concurrent.csv`, `<op>_errors.csv`, `<op>_throttles.csv`) into
   `load-tests/results/cloudwatch/`.
2. Run `python analysis/cloudwatch/analyze_cloudwatch.py` and check the
   logged offset matches the timezone you used in the AWS Console.
3. Run `python analysis/cross_reference/compare_locust_vs_cloudwatch.py`.

If you want to change the display timezone (say, the next assignment is read
by a Chilean professor), edit the single constant `DISPLAY_TZ` at the top of
`analysis/_tz_helper.py`. Everything follows.

---

## In the report

Reference figure captions should include the timezone, e.g.:

> *Figure 4. Concurrent Lambda executions over time (Europe/Rome).*

This avoids ambiguity for the reader and credits the convention.
