"""Reads crop_profiles.json, the single source of crop values. No crop number lives in code."""

import json
from pathlib import Path

from engine import CropProfile


class ProfilesError(RuntimeError):
    """Startup is refused: the crop file is missing or not what the engine needs."""


def load_crop_profiles(path: Path) -> dict[str, CropProfile]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProfilesError(f"Cannot read crop profiles file {path}: {exc}") from None
    result: dict[str, CropProfile] = {}
    for crop_id, entry in raw.items():
        if crop_id.startswith("_"):  # "_readme" and similar notes
            continue
        try:
            rows = [row for row in entry["stage_rows"] if row.get("default")]
            if len(rows) != 1:
                raise ValueError("needs exactly one stage row with \"default\": true")
            row = rows[0]
            result[crop_id] = CropProfile(
                kc_ini=float(entry["kc_ini"]["value"]),
                kc_mid=float(entry["kc_mid"]["value"]),
                kc_end=float(entry["kc_end"]["value"]),
                height_m=float(entry["height_m"]["value"]),
                init_days=int(row["init_days"]),
                dev_days=int(row["dev_days"]),
                mid_days=int(row["mid_days"]),
                late_days=int(row["late_days"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProfilesError(f"Crop profile '{crop_id}' in {path} is invalid: {exc!r}") from None
    return result
