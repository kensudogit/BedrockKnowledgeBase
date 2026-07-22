import pytest

from src.services import credit_info as ci


def test_credit_subject_contract_score_flow():
    sub = ci.register_subject(
        full_name="山田太郎",
        birth_date="1990-01-15",
        phone="09012345678",
        email="yama@example.com",
        external_ref="EXT-1",
    )
    assert "full_name_masked" in sub
    assert sub["full_name_masked"].startswith("山")
    assert "****5678" in sub["phone_masked"] or sub["phone_masked"].endswith("5678")

    sid = sub["subject_id"]
    assert ci.get_subject(sid) is not None

    ci.add_contract(
        subject_id=sid,
        contract_type="credit_card",
        lender="Demo Card",
        credit_limit=500_000,
        balance=100_000,
        payment_status="current",
    )
    ci.add_contract(
        subject_id=sid,
        contract_type="loan",
        lender="Demo Bank",
        credit_limit=1_000_000,
        balance=900_000,
        payment_status="late",
        months_delinquent=2,
    )

    with pytest.raises(PermissionError):
        ci.record_inquiry(subject_id=sid, requester="Lender A", require_consent=True)

    consent = ci.record_consent(subject_id=sid, purpose="credit_inquiry", requester="Lender A")
    assert consent["status"] == "granted"

    inq = ci.record_inquiry(subject_id=sid, requester="Lender A", inquiry_type="hard")
    assert inq["inquiry_id"]

    score = ci.compute_score(sid)
    assert 300 <= score["score"] <= 850
    assert score["band"]
    assert score["open_contracts"] == 2

    report = ci.build_report(sid)
    assert report["subject"]["subject_id"] == sid
    assert len(report["contracts"]) == 2
    assert report["score"]["score"] == score["score"]

    audit = ci.list_audit(subject_id=sid)
    assert any(a["action"] == "consent.grant" for a in audit)
    assert any(a["action"] == "inquiry.record" for a in audit)


def test_credit_report_not_found():
    with pytest.raises(ValueError):
        ci.build_report("missing-id")
