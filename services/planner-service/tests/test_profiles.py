import json

import pytest

import profiles


def test_loads_default_stage_row_and_values(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"_readme": "x", "beet": {
        "kc_ini": {"value": 0.5}, "kc_mid": {"value": 1.0}, "kc_end": {"value": 0.9}, "height_m": {"value": 0.4},
        "stage_rows": [
            {"init_days": 1, "dev_days": 1, "mid_days": 1, "late_days": 1},
            {"init_days": 10, "dev_days": 20, "mid_days": 30, "late_days": 40, "default": True}]}}))
    beet = profiles.load_crop_profiles(path)["beet"]
    assert (beet.kc_ini, beet.kc_mid, beet.kc_end, beet.height_m) == (0.5, 1.0, 0.9, 0.4)
    assert (beet.init_days, beet.dev_days, beet.mid_days, beet.late_days) == (10, 20, 30, 40)


def test_missing_file_is_a_clear_error(tmp_path):
    with pytest.raises(profiles.ProfilesError, match="crop profiles"):
        profiles.load_crop_profiles(tmp_path / "nope.json")


def test_crop_without_default_row_is_a_clear_error(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"beet": {"kc_ini": {"value": 0.5}, "kc_mid": {"value": 1.0},
        "kc_end": {"value": 0.9}, "height_m": {"value": 0.4}, "stage_rows": []}}))
    with pytest.raises(profiles.ProfilesError, match="beet"):
        profiles.load_crop_profiles(path)
