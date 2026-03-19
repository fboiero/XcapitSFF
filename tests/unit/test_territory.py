"""Tests for territory management."""

from xcapitsff.sales.territory import Territory, TerritoryManager


def test_default_territories():
    tm = TerritoryManager()
    territories = tm.list_territories()
    assert len(territories) >= 4


def test_assign_latam_enterprise():
    tm = TerritoryManager()
    assignment = tm.assign_lead(1, {
        "region": "LATAM", "score_icp": 85, "c_level": True,
    })
    assert assignment is not None
    assert assignment.territory_id == "latam-enterprise"


def test_assign_latam_mid():
    tm = TerritoryManager()
    assignment = tm.assign_lead(1, {
        "region": "LATAM", "score_icp": 50, "c_level": False,
    })
    assert assignment is not None
    assert assignment.territory_id == "latam-mid"


def test_assign_latam_smb():
    tm = TerritoryManager()
    assignment = tm.assign_lead(1, {
        "region": "LATAM", "score_icp": 20, "c_level": False,
    })
    assert assignment is not None
    assert assignment.territory_id == "latam-smb"


def test_assign_iberia():
    tm = TerritoryManager()
    assignment = tm.assign_lead(1, {"region": "Iberia", "score_icp": 50})
    assert assignment is not None
    assert assignment.territory_id == "iberia-all"


def test_round_robin_reps():
    tm = TerritoryManager()
    a1 = tm.assign_lead(1, {"region": "LATAM", "score_icp": 50})
    a2 = tm.assign_lead(2, {"region": "LATAM", "score_icp": 55})
    # Should cycle through reps
    assert a1.assigned_rep != a2.assigned_rep or len(tm.get_territory("latam-mid").assigned_reps) == 1


def test_capacity_limit():
    tm = TerritoryManager()
    # Set very low capacity
    tm._territories["latam-smb"].max_leads = 1
    tm.assign_lead(1, {"region": "LATAM", "score_icp": 20})
    assignment = tm.assign_lead(2, {"region": "LATAM", "score_icp": 20})
    # Should fall back to mid or be None
    assert assignment is None or assignment.territory_id != "latam-smb"


def test_get_lead_territory():
    tm = TerritoryManager()
    tm.assign_lead(42, {"region": "LATAM", "score_icp": 75, "c_level": True})
    assert tm.get_lead_territory(42) == "latam-enterprise"
    assert tm.get_lead_territory(999) is None


def test_stats():
    tm = TerritoryManager()
    tm.assign_lead(1, {"region": "LATAM", "score_icp": 80, "c_level": True})
    stats = tm.get_stats()
    assert stats["total"] >= 4
    assert any("1/" in t["capacity"] for t in stats["territories"])
