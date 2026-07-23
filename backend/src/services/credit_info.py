"""信用情報管理 — 本人・契約・照会・同意・スコア（デモ用ローカル永続化）。"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.services import persist

_SUBJECTS = "credit_subjects"
_CONTRACTS = "credit_contracts"
_INQUIRIES = "credit_inquiries"
_CONSENTS = "credit_consents"
_AUDIT = "credit_audit"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(action: str, *, subject_id: str | None = None, meta: dict[str, Any] | None = None) -> None:
    persist.append(
        _AUDIT,
        {
            "audit_id": str(uuid4()),
            "action": action,
            "subject_id": subject_id,
            "meta": meta or {},
            "created_at": _now(),
        },
    )


def _mask_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "***"
    if len(name) == 1:
        return "*"
    return name[0] + "*" * (len(name) - 1)


def _mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 4:
        return "***"
    return "*" * (len(digits) - 4) + digits[-4:]


def _hash_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def register_subject(
    *,
    full_name: str,
    birth_date: str,
    phone: str = "",
    email: str = "",
    external_ref: str = "",
    notes: str = "",
) -> dict[str, Any]:
    """信用情報の本人（被照会者）を新規登録する。"""
    subject_id = str(uuid4())
    item = {
        "subject_id": subject_id,
        "full_name": full_name.strip(),
        "birth_date": birth_date.strip(),
        "phone": phone.strip(),
        "email": email.strip(),
        "external_ref": external_ref.strip(),
        "notes": notes.strip(),
        "status": "active",
        "name_hash": _hash_id(full_name.strip().lower()),
        "created_at": _now(),
        "updated_at": _now(),
    }
    persist.append(_SUBJECTS, item)
    _audit("subject.register", subject_id=subject_id, meta={"external_ref": external_ref})
    return public_subject(item)


def public_subject(item: dict[str, Any], *, reveal: bool = False) -> dict[str, Any]:
    """本人情報を公開用形式に変換する。reveal=True でマスクなし。"""
    if reveal:
        return {
            "subject_id": item["subject_id"],
            "full_name": item.get("full_name"),
            "birth_date": item.get("birth_date"),
            "phone": item.get("phone"),
            "email": item.get("email"),
            "external_ref": item.get("external_ref"),
            "notes": item.get("notes"),
            "status": item.get("status"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
    return {
        "subject_id": item["subject_id"],
        "full_name_masked": _mask_name(str(item.get("full_name") or "")),
        "birth_date": item.get("birth_date"),
        "phone_masked": _mask_phone(str(item.get("phone") or "")),
        "email_set": bool(item.get("email")),
        "external_ref": item.get("external_ref"),
        "status": item.get("status"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


def list_subjects(limit: int = 100) -> list[dict[str, Any]]:
    """登録済み本人一覧をマスク付きで返す。"""
    items = persist.load(_SUBJECTS)
    return [public_subject(x) for x in items[-limit:]]


def get_subject(subject_id: str, *, reveal: bool = False) -> dict[str, Any] | None:
    """指定 ID の本人情報を取得する。"""
    for item in persist.load(_SUBJECTS):
        if item.get("subject_id") == subject_id:
            return public_subject(item, reveal=reveal)
    return None


def _raw_subject(subject_id: str) -> dict[str, Any] | None:
    for item in persist.load(_SUBJECTS):
        if item.get("subject_id") == subject_id:
            return item
    return None


def add_contract(
    *,
    subject_id: str,
    contract_type: str,
    lender: str,
    credit_limit: int = 0,
    balance: int = 0,
    status: str = "open",
    opened_on: str = "",
    payment_status: str = "current",
    months_delinquent: int = 0,
) -> dict[str, Any]:
    """本人に紐づく契約（カード・ローン等）を追加する。"""
    if not _raw_subject(subject_id):
        raise ValueError("subject not found")
    item = {
        "contract_id": str(uuid4()),
        "subject_id": subject_id,
        "contract_type": contract_type,  # credit_card | loan | mortgage | other
        "lender": lender,
        "credit_limit": int(credit_limit),
        "balance": int(balance),
        "status": status,
        "opened_on": opened_on or _now()[:10],
        "payment_status": payment_status,  # current | late | charged_off
        "months_delinquent": int(months_delinquent),
        "created_at": _now(),
    }
    persist.append(_CONTRACTS, item)
    _audit(
        "contract.add",
        subject_id=subject_id,
        meta={"contract_id": item["contract_id"], "contract_type": contract_type},
    )
    return item


def list_contracts(subject_id: str) -> list[dict[str, Any]]:
    """指定本人の契約一覧を返す。"""
    return [c for c in persist.load(_CONTRACTS) if c.get("subject_id") == subject_id]


def record_consent(
    *,
    subject_id: str,
    purpose: str,
    requester: str,
    channel: str = "web",
    expires_at: str = "",
) -> dict[str, Any]:
    """信用情報照会の同意を記録する。"""
    if not _raw_subject(subject_id):
        raise ValueError("subject not found")
    item = {
        "consent_id": str(uuid4()),
        "subject_id": subject_id,
        "purpose": purpose,
        "requester": requester,
        "channel": channel,
        "status": "granted",
        "expires_at": expires_at or None,
        "created_at": _now(),
    }
    persist.append(_CONSENTS, item)
    _audit("consent.grant", subject_id=subject_id, meta={"consent_id": item["consent_id"], "purpose": purpose})
    return item


def list_consents(subject_id: str) -> list[dict[str, Any]]:
    """指定本人の同意履歴を返す。"""
    return [c for c in persist.load(_CONSENTS) if c.get("subject_id") == subject_id]


def has_valid_consent(subject_id: str, purpose: str) -> bool:
    """指定目的に対する有効な同意があるか判定する。"""
    now = datetime.now(timezone.utc)
    for c in list_consents(subject_id):
        if c.get("status") != "granted":
            continue
        if c.get("purpose") not in {purpose, "all", "credit_inquiry"}:
            continue
        exp = c.get("expires_at")
        if exp:
            try:
                exp_dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
                if exp_dt < now:
                    continue
            except ValueError:
                pass
        return True
    return False


def record_inquiry(
    *,
    subject_id: str,
    requester: str,
    purpose: str = "credit_review",
    inquiry_type: str = "hard",
    require_consent: bool = True,
) -> dict[str, Any]:
    """信用照会を記録する。require_consent 時は有効な同意が必要。"""
    if not _raw_subject(subject_id):
        raise ValueError("subject not found")
    if require_consent and not has_valid_consent(subject_id, purpose):
        raise PermissionError("valid consent required for credit inquiry")
    item = {
        "inquiry_id": str(uuid4()),
        "subject_id": subject_id,
        "requester": requester,
        "purpose": purpose,
        "inquiry_type": inquiry_type,  # hard | soft
        "created_at": _now(),
    }
    persist.append(_INQUIRIES, item)
    _audit(
        "inquiry.record",
        subject_id=subject_id,
        meta={"inquiry_id": item["inquiry_id"], "requester": requester, "inquiry_type": inquiry_type},
    )
    return item


def list_inquiries(subject_id: str) -> list[dict[str, Any]]:
    """指定本人の照会履歴を返す。"""
    return [i for i in persist.load(_INQUIRIES) if i.get("subject_id") == subject_id]


def compute_score(subject_id: str) -> dict[str, Any]:
    """契約・照会情報から簡易信用スコア（300–850）を算出する。"""
    contracts = list_contracts(subject_id)
    inquiries = list_inquiries(subject_id)
    score = 720
    reasons: list[str] = []

    if not contracts:
        score -= 40
        reasons.append("契約情報なし（ベース減点）")

    open_contracts = [c for c in contracts if c.get("status") == "open"]
    total_limit = sum(int(c.get("credit_limit") or 0) for c in open_contracts) or 0
    total_balance = sum(int(c.get("balance") or 0) for c in open_contracts) or 0
    util = (total_balance / total_limit) if total_limit > 0 else 0.0
    if util > 0.8:
        score -= 60
        reasons.append(f"利用率が高い ({util:.0%})")
    elif util > 0.5:
        score -= 25
        reasons.append(f"利用率やや高い ({util:.0%})")
    elif total_limit > 0:
        score += 15
        reasons.append(f"利用率健全 ({util:.0%})")

    late = [c for c in contracts if c.get("payment_status") in {"late", "charged_off"}]
    for c in late:
        months = int(c.get("months_delinquent") or 1)
        pen = 30 + min(months, 12) * 5
        score -= pen
        reasons.append(f"延滞: {c.get('lender')} ({months}ヶ月相当 −{pen})")

    hard = [i for i in inquiries if i.get("inquiry_type") == "hard"]
    recent_hard = hard[-6:]
    if len(recent_hard) >= 4:
        score -= 35
        reasons.append(f"ハード照会が多い ({len(recent_hard)}件)")
    elif len(recent_hard) >= 2:
        score -= 15
        reasons.append(f"ハード照会あり ({len(recent_hard)}件)")

    if any(c.get("contract_type") == "mortgage" and c.get("payment_status") == "current" for c in contracts):
        score += 20
        reasons.append("住宅ローン良好")

    score = max(300, min(850, score))
    band = (
        "excellent"
        if score >= 760
        else "good"
        if score >= 700
        else "fair"
        if score >= 640
        else "poor"
        if score >= 580
        else "very_poor"
    )
    return {
        "subject_id": subject_id,
        "score": score,
        "band": band,
        "utilization": round(util, 4),
        "open_contracts": len(open_contracts),
        "total_credit_limit": total_limit,
        "total_balance": total_balance,
        "hard_inquiries": len(hard),
        "reasons": reasons,
        "computed_at": _now(),
    }


def build_report(subject_id: str, *, reveal: bool = False) -> dict[str, Any]:
    """本人・契約・照会・同意・スコアを含む信用レポートを生成する。"""
    subject = get_subject(subject_id, reveal=reveal)
    if not subject:
        raise ValueError("subject not found")
    contracts = list_contracts(subject_id)
    inquiries = list_inquiries(subject_id)
    consents = list_consents(subject_id)
    score = compute_score(subject_id)
    _audit("report.view", subject_id=subject_id, meta={"reveal": reveal})
    return {
        "subject": subject,
        "contracts": contracts,
        "inquiries": inquiries,
        "consents": consents,
        "score": score,
        "generated_at": _now(),
    }


def list_audit(limit: int = 100, subject_id: str | None = None) -> list[dict[str, Any]]:
    """監査ログを返す。subject_id 指定時は本人でフィルタ。"""
    items = persist.load(_AUDIT)
    if subject_id:
        items = [a for a in items if a.get("subject_id") == subject_id]
    return items[-limit:]
