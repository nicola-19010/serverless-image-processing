"""
Shared timezone detection helper.

CloudWatch CSVs from the AWS Console may be exported in either UTC or local
time depending on the downloader's browser/OS settings.  In our team:

  - resize    (Nico's machine in Italy, AWS default "local timezone")  -> Rome / UTC+2
  - grayscale (Prajwal's machine in Italy, AWS default "local timezone") -> Rome / UTC+2
  - edge      (Mathias selected UTC explicitly in AWS console)           -> UTC

To make this robust regardless of who downloads next time, we auto-detect each
CSV's timezone by comparing the busiest minute in invocations.csv with the
midpoint of the Locust scenarios for that operation (Locust always uses
unambiguous UTC epoch timestamps).

All scripts normalise to a single display timezone (Europe/Rome) so that the
charts in the final report read naturally for a reader at Sapienza.
"""

from pathlib import Path
import pandas as pd

DISPLAY_TZ = "Europe/Rome"


def find_header_row(path):
    """AWS Console exports prepend 5 metadata rows; find the 'Label' row."""
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i > 10:
                break
            first_cell = line.split(",", 1)[0].strip().strip('"').lower()
            if first_cell == "label":
                return i
    return 0


def detect_csv_offset_hours(inv_path: Path, locust_mid_utc: pd.Timestamp) -> int:
    """
    Compare the busiest minute in an invocations CSV against the midpoint of
    the corresponding Locust window (which is in UTC).  Returns the integer
    number of hours the CSV is offset from UTC.
    """
    h = find_header_row(inv_path)
    df = pd.read_csv(inv_path, header=h)
    cols = list(df.columns)
    df = df[[cols[0], cols[1]]].rename(columns={cols[0]: "timestamp", cols[1]: "inv"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["inv"] = pd.to_numeric(df["inv"], errors="coerce")
    df = df.dropna()
    if df.empty:
        return 0
    busy = df.loc[df["inv"].idxmax(), "timestamp"]
    locust_mid_naive = locust_mid_utc.tz_convert(None) if locust_mid_utc.tzinfo else locust_mid_utc
    diff_seconds = (busy - locust_mid_naive).total_seconds()
    return round(diff_seconds / 3600)


def to_display_tz(series_naive: pd.Series, csv_offset_h: int) -> pd.Series:
    """
    Given a naive timestamp series whose original offset from UTC is
    csv_offset_h, return the same series localised to DISPLAY_TZ (Europe/Rome).
    """
    # Step 1: subtract the offset to make it true UTC.
    utc_series = series_naive - pd.Timedelta(hours=csv_offset_h)
    # Step 2: label as UTC, then convert to display tz.
    return utc_series.dt.tz_localize("UTC").dt.tz_convert(DISPLAY_TZ)
