"""
test_validation.py

Unit tests for validate_data.py and metadata tables.
Validates that the automated validation gate runs with 0 errors,
and all 4 provenance and limitation catalogs are populated.
"""

from pathlib import Path
import pandas as pd
import pytest
from src.validate_data import validate_all


@pytest.fixture(scope="module")
def root_dir():
    return Path(__file__).resolve().parent.parent


def test_validation_gate_zero_errors(root_dir):
    """Asserts the master validation gate reports zero errors and zero warnings."""
    result = validate_all(root_dir)
    assert len(result["errors"]) == 0, f"Validation errors found: {result['errors']}"
    assert len(result["warnings"]) == 0, f"Validation warnings found: {result['warnings']}"
    assert result["ifct_foods"] == 542
    assert result["ingredients"] == 80
    assert result["dishes"] == 132
    assert result["insufficient_data"] == 17
    assert result["complete_nutrition"] == 115


def test_metadata_tables_exist_and_populated(root_dir):
    """Asserts all 4 metadata catalogs exist with required content."""
    meta_dir = root_dir / "data" / "metadata"
    sources_df = pd.read_csv(meta_dir / "source_registry.csv")
    prov_df = pd.read_csv(meta_dir / "data_provenance.csv")
    limits_df = pd.read_csv(meta_dir / "limitations.csv")
    dict_df = pd.read_csv(meta_dir / "data_dictionary.csv")

    assert len(sources_df) >= 5
    assert "SRC_IFCT2017_PUB" in sources_df["source_id"].values
    assert "SRC_ATWATER_FAO2003" in sources_df["source_id"].values

    assert len(prov_df) >= 7
    assert "IFCT_DERIVED" in prov_df["source_type"].values

    assert len(limits_df) >= 5
    assert "LIM_002" in limits_df["limitation_id"].values  # Sodium lower bound

    assert len(dict_df) >= 15
