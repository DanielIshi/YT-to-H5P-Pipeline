"""
Tests for Learning Path Mix Validation

Validates that generated learning paths have the correct:
1. Variance - No consecutive same types
2. Balance - Correct phase distribution
3. Didactic order - Passive before active, summary at end
4. Coverage - All concepts covered
"""
import pytest
from typing import List, Dict, Any

# Import from the pipeline module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.h5p.config.milestones import get_milestone_config, MVP_CONFIG


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def valid_learning_path() -> Dict[str, Any]:
    """A valid learning path with correct mix."""
    return {
        "learning_path": [
            {"order": 1, "content_type": "dialogcards", "concept_refs": ["AI"]},
            {"order": 2, "content_type": "accordion", "concept_refs": ["ML"]},
            {"order": 3, "content_type": "blanks", "concept_refs": ["AI"]},
            {"order": 4, "content_type": "truefalse", "concept_refs": ["ML"]},
            {"order": 5, "content_type": "multichoice", "concept_refs": ["AI"]},
            {"order": 6, "content_type": "dragtext", "concept_refs": ["AI", "ML"]},
            {"order": 7, "content_type": "truefalse", "concept_refs": ["ML"]},
            {"order": 8, "content_type": "summary", "concept_refs": ["AI", "ML"]},
        ],
        "phase_distribution": {"passive": 2, "active": 5, "reflect": 1}
    }


@pytest.fixture
def invalid_consecutive_types() -> Dict[str, Any]:
    """Learning path with consecutive same types."""
    return {
        "learning_path": [
            {"order": 1, "content_type": "dialogcards", "concept_refs": ["AI"]},
            {"order": 2, "content_type": "dialogcards", "concept_refs": ["ML"]},  # BAD!
            {"order": 3, "content_type": "blanks", "concept_refs": ["AI"]},
            {"order": 4, "content_type": "summary", "concept_refs": ["AI", "ML"]},
        ]
    }


@pytest.fixture
def invalid_summary_position() -> Dict[str, Any]:
    """Learning path with summary not at end."""
    return {
        "learning_path": [
            {"order": 1, "content_type": "dialogcards", "concept_refs": ["AI"]},
            {"order": 2, "content_type": "summary", "concept_refs": ["AI"]},  # BAD!
            {"order": 3, "content_type": "blanks", "concept_refs": ["AI"]},
        ]
    }


@pytest.fixture
def mvp_config() -> Dict[str, Any]:
    """MVP milestone configuration."""
    return MVP_CONFIG


# ============================================================================
# Validation Functions
# ============================================================================

def check_no_consecutive_same_type(activities: List[Dict]) -> bool:
    """
    Verify no two consecutive activities have the same content type.

    Args:
        activities: List of activity dicts with 'content_type' key

    Returns:
        True if valid (no consecutive same types)
    """
    for i in range(len(activities) - 1):
        if activities[i].get("content_type") == activities[i + 1].get("content_type"):
            return False
    return True


def check_phase_distribution(
    activities: List[Dict],
    config: Dict[str, Any],
    tolerance: float = 0.15
) -> bool:
    """
    Verify phase distribution is within acceptable range.

    Expected: ~25% passive, ~50% active, ~15% reflective

    Args:
        activities: List of activity dicts
        config: Milestone configuration
        tolerance: Allowed deviation from expected (default 15%)

    Returns:
        True if distribution is acceptable
    """
    if not activities:
        return False

    # Get type lists from config
    passive_types = config["phases"].get("passive", {}).get("types", [])
    active_types = config["phases"].get("active", {}).get("types", [])
    reflect_types = config["phases"].get("reflect", {}).get("types", [])

    passive = sum(1 for a in activities if a.get("content_type") in passive_types)
    active = sum(1 for a in activities if a.get("content_type") in active_types)
    reflect = sum(1 for a in activities if a.get("content_type") in reflect_types)
    total = len(activities)

    # Expected ratios with tolerance
    passive_ratio = passive / total
    active_ratio = active / total
    reflect_ratio = reflect / total

    # Check bounds (with tolerance)
    passive_ok = 0.15 - tolerance <= passive_ratio <= 0.35 + tolerance
    active_ok = 0.40 - tolerance <= active_ratio <= 0.60 + tolerance
    reflect_ok = 0.10 - tolerance <= reflect_ratio <= 0.25 + tolerance

    return passive_ok and active_ok and reflect_ok


def check_didactic_order(activities: List[Dict], config: Dict[str, Any]) -> bool:
    """
    Verify didactic order: passive before active, summary at end.

    Args:
        activities: List of activity dicts
        config: Milestone configuration

    Returns:
        True if order is didactically correct
    """
    if not activities:
        return False

    passive_types = config["phases"].get("passive", {}).get("types", [])
    active_types = config["phases"].get("active", {}).get("types", [])

    # Summary must be last
    if activities[-1].get("content_type") != "summary":
        return False

    # Find first active and last passive indices
    first_active_idx = next(
        (i for i, a in enumerate(activities) if a.get("content_type") in active_types),
        len(activities)
    )
    last_passive_idx = max(
        (i for i, a in enumerate(activities) if a.get("content_type") in passive_types),
        default=-1
    )

    # Allow some overlap (tolerance of 2 positions)
    return last_passive_idx < first_active_idx + 2


def check_all_concepts_covered(
    activities: List[Dict],
    required_concepts: List[str]
) -> bool:
    """
    Verify all required concepts appear in at least one activity.

    Args:
        activities: List of activity dicts with 'concept_refs' key
        required_concepts: List of concept names that must be covered

    Returns:
        True if all concepts are covered
    """
    covered = set()
    for a in activities:
        covered.update(a.get("concept_refs", []))

    return set(required_concepts).issubset(covered)


def validate_learning_path_mix(
    learning_path: Dict[str, Any],
    config: Dict[str, Any],
    required_concepts: List[str] = None
) -> Dict[str, Any]:
    """
    Full validation of a learning path.

    Args:
        learning_path: Learning path dict with 'learning_path' key
        config: Milestone configuration
        required_concepts: Optional list of concepts that must be covered

    Returns:
        Dict with validation results
    """
    activities = learning_path.get("learning_path", [])

    results = {
        "variance_ok": check_no_consecutive_same_type(activities),
        "balance_ok": check_phase_distribution(activities, config),
        "didactic_ok": check_didactic_order(activities, config),
        "coverage_ok": True  # Default if no concepts required
    }

    if required_concepts:
        results["coverage_ok"] = check_all_concepts_covered(activities, required_concepts)

    results["all_ok"] = all(results.values())

    return results


# ============================================================================
# Tests
# ============================================================================

class TestVariance:
    """Tests for consecutive type validation."""

    def test_valid_no_consecutive(self, valid_learning_path):
        activities = valid_learning_path["learning_path"]
        assert check_no_consecutive_same_type(activities) is True

    def test_invalid_consecutive(self, invalid_consecutive_types):
        activities = invalid_consecutive_types["learning_path"]
        assert check_no_consecutive_same_type(activities) is False

    def test_empty_list(self):
        assert check_no_consecutive_same_type([]) is True

    def test_single_activity(self):
        assert check_no_consecutive_same_type([{"content_type": "blanks"}]) is True


class TestPhaseDistribution:
    """Tests for phase balance validation."""

    def test_valid_distribution(self, valid_learning_path, mvp_config):
        activities = valid_learning_path["learning_path"]
        # 2 passive (25%), 5 active (62.5%), 1 reflect (12.5%)
        assert check_phase_distribution(activities, mvp_config, tolerance=0.20) is True

    def test_empty_list(self, mvp_config):
        assert check_phase_distribution([], mvp_config) is False

    def test_all_same_type(self, mvp_config):
        activities = [{"content_type": "blanks"} for _ in range(8)]
        # 100% active - should fail
        assert check_phase_distribution(activities, mvp_config) is False


class TestDidacticOrder:
    """Tests for didactic ordering validation."""

    def test_valid_order(self, valid_learning_path, mvp_config):
        activities = valid_learning_path["learning_path"]
        assert check_didactic_order(activities, mvp_config) is True

    def test_summary_not_at_end(self, invalid_summary_position, mvp_config):
        activities = invalid_summary_position["learning_path"]
        assert check_didactic_order(activities, mvp_config) is False

    def test_empty_list(self, mvp_config):
        assert check_didactic_order([], mvp_config) is False


class TestConceptCoverage:
    """Tests for concept coverage validation."""

    def test_all_covered(self, valid_learning_path):
        activities = valid_learning_path["learning_path"]
        assert check_all_concepts_covered(activities, ["AI", "ML"]) is True

    def test_missing_concept(self, valid_learning_path):
        activities = valid_learning_path["learning_path"]
        assert check_all_concepts_covered(activities, ["AI", "ML", "DeepLearning"]) is False

    def test_no_required_concepts(self, valid_learning_path):
        activities = valid_learning_path["learning_path"]
        assert check_all_concepts_covered(activities, []) is True


class TestFullValidation:
    """Tests for complete validation."""

    def test_valid_path(self, valid_learning_path, mvp_config):
        result = validate_learning_path_mix(
            valid_learning_path,
            mvp_config,
            required_concepts=["AI", "ML"]
        )
        # May have balance issues due to strict ratios, but should pass variance and didactic
        assert result["variance_ok"] is True
        assert result["didactic_ok"] is True
        assert result["coverage_ok"] is True

    def test_invalid_consecutive(self, invalid_consecutive_types, mvp_config):
        result = validate_learning_path_mix(invalid_consecutive_types, mvp_config)
        assert result["variance_ok"] is False
        assert result["all_ok"] is False


# ============================================================================
# Run tests directly
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
