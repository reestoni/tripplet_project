"""One-off: adds tblTrialSettings.DYRatio and fills it from T1/T2 for all
existing plies (see db/dy_ratio.py). Safe to run again (only rows whose
value differs are touched).

    python tools/backfill_dy_ratio.py dev_local
    python tools/backfill_dy_ratio.py prod      # only with explicit permission
"""
import os
import sys

if len(sys.argv) != 2 or sys.argv[1] not in ("dev_local", "dev", "prod"):
    sys.exit(__doc__)
os.environ["TRIPPLET_MODE"] = sys.argv[1]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import dy_ratio  # noqa: E402
from db.connection import fetch_all  # noqa: E402

dy_ratio.add_column()
print("changed rows:", dy_ratio.recompute())
print(fetch_all("SELECT COUNT(*) AS plies, SUM(DYRatio IS NOT NULL) AS with_ratio, "
                "MIN(DYRatio) AS min_ratio, MAX(DYRatio) AS max_ratio FROM tblTrialSettings")[0])
