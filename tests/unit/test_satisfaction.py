"""Tests for customer satisfaction tracking."""

from xcapitsff.support.satisfaction import SatisfactionTracker


def test_record_csat():
    tracker = SatisfactionTracker()
    resp = tracker.record_csat(1, 100, 5, "Excelente servicio")
    assert resp.rating.value == 5
    assert resp.comment == "Excelente servicio"


def test_record_nps():
    tracker = SatisfactionTracker()
    resp = tracker.record_nps(100, 9, "Recomendaría")
    assert resp.score == 9
    assert resp.category == "promoter"


def test_nps_categories():
    tracker = SatisfactionTracker()
    p = tracker.record_nps(1, 10)
    assert p.category == "promoter"
    pa = tracker.record_nps(2, 8)
    assert pa.category == "passive"
    d = tracker.record_nps(3, 5)
    assert d.category == "detractor"


def test_csat_average():
    tracker = SatisfactionTracker()
    tracker.record_csat(1, 100, 5)
    tracker.record_csat(2, 101, 3)
    tracker.record_csat(3, 102, 4)
    avg = tracker.get_csat_average()
    assert avg == 4.0


def test_csat_average_empty():
    tracker = SatisfactionTracker()
    assert tracker.get_csat_average() is None


def test_nps_score():
    tracker = SatisfactionTracker()
    # 3 promoters, 1 passive, 1 detractor
    tracker.record_nps(1, 10)
    tracker.record_nps(2, 9)
    tracker.record_nps(3, 10)
    tracker.record_nps(4, 8)
    tracker.record_nps(5, 3)
    nps = tracker.get_nps_score()
    # (3 - 1) / 5 * 100 = 40
    assert nps == 40.0


def test_nps_empty():
    tracker = SatisfactionTracker()
    assert tracker.get_nps_score() is None


def test_report():
    tracker = SatisfactionTracker()
    tracker.record_csat(1, 100, 5, "Muy bien")
    tracker.record_csat(2, 101, 1, "Pésimo servicio")
    tracker.record_nps(100, 10)
    tracker.record_nps(101, 2)

    report = tracker.get_report()
    assert report.csat_responses == 2
    assert report.nps_responses == 2
    assert len(report.top_complaints) >= 1
    assert len(report.top_praises) >= 1


def test_customer_satisfaction():
    tracker = SatisfactionTracker()
    tracker.record_csat(1, 42, 5)
    tracker.record_csat(2, 42, 4)
    tracker.record_nps(42, 9)

    sat = tracker.get_customer_satisfaction(42)
    assert sat["csat_count"] == 2
    assert sat["csat_average"] == 4.5
    assert sat["latest_nps"] == 9
    assert sat["nps_category"] == "promoter"


def test_customer_no_data():
    tracker = SatisfactionTracker()
    sat = tracker.get_customer_satisfaction(999)
    assert sat["csat_count"] == 0
    assert sat["csat_average"] is None
    assert sat["latest_nps"] is None


def test_csat_clamped():
    tracker = SatisfactionTracker()
    resp = tracker.record_csat(1, 100, 10)  # over 5
    assert resp.rating.value == 5
