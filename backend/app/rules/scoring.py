from __future__ import annotations

from app.rules.models import RuleResult

DOCUMENT_FAIL_SCORE = 25
RISK_LEVELS = {
    0: "low",
    25: "lower",
    50: "medium",
    75: "higher",
    100: "high",
}


def score_document(rule_results: list[RuleResult]) -> int:
    if any(rule.status == "fail" for rule in rule_results):
        return DOCUMENT_FAIL_SCORE
    return 0


def score_assessment(document_scores: dict[str, int]) -> int:
    total = (
        int(document_scores.get("id_100", 0))
        + int(document_scores.get("payslip", 0))
        + int(document_scores.get("bank_statement_3m", 0))
        + int(document_scores.get("ato_notice", 0))
    )
    if total not in RISK_LEVELS:
        raise ValueError(f"Invalid overall risk score: {total}")
    return total


def risk_level_for_score(score: int) -> str:
    try:
        return RISK_LEVELS[score]
    except KeyError as error:
        raise ValueError(f"Unsupported risk score: {score}") from error


def document_status_for_score(score: int) -> str:
    return "fail" if score > 0 else "pass"
