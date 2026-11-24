"""4-layer prompt injection detection for SentryFlow.

Layer 1: Regex/pattern matching (deterministic)
Layer 2: Canary token verification (deterministic)
Layer 3: Structural boundary analysis (deterministic)
Layer 4: Optional LLM classifier (advisory only)

IMPORTANT: These layers are supplementary detection signals, NOT authorization
guarantees. The policy engine makes the final authorization decision.
"""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass, field
from typing import Any

INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?previous\s+instructions?", 90, "instruction_override"),
    (r"forget\s+(all\s+)?previous\s+(instructions?|context)", 90, "instruction_override"),
    (r"disregard\s+(all\s+)?(prior|previous|above)\s+", 85, "instruction_override"),
    (r"you\s+are\s+now\s+a?\s*", 60, "role_hijack"),
    (r"act\s+as\s+(if\s+you\s+are|a)\s+", 55, "role_hijack"),
    (r"pretend\s+(you\s+are|to\s+be)\s+", 55, "role_hijack"),
    (r"system\s*prompt\s*:", 80, "system_prompt_injection"),
    (r"\[system\]", 75, "system_prompt_injection"),
    (r"<\s*system\s*>", 75, "system_prompt_injection"),
    (r"execute\s+(this\s+)?(command|code|script)", 70, "code_execution"),
    (r"run\s+(this\s+)?(command|code|script)", 65, "code_execution"),
    (r"admin\s*access|grant\s*(me\s+)?admin|elevate\s+privileges?", 80, "privilege_escalation"),
    (r"bypass\s+(security|authentication|authorization|approval)", 90, "security_bypass"),
    (r"skip\s+(verification|validation|check|approval)", 85, "security_bypass"),
    (r"approve\s+(all|this|the)\s+(payment|transaction|request)", 75, "auto_approve"),
    (r"authorized?\s+by\s+(management|cfo|ceo|admin)", 70, "false_authority"),
    (r"urgent.{0,30}(skip|bypass|override)\s+", 65, "urgency_manipulation"),
    (r"\\n\s*\\n\s*---+\s*\\n", 50, "delimiter_injection"),
    (r"</?(?:script|iframe|object|embed)", 60, "html_injection"),
    (r"(?:GRANT|DROP|DELETE|UPDATE|INSERT)\s+", 55, "sql_injection"),
]

STRUCTURAL_DELIMITERS = [
    "</untrusted_document>",
    "</system>",
    "</instructions>",
    "END OF DOCUMENT",
    "---BEGIN INSTRUCTIONS---",
]


@dataclass
class ScanResult:
    score: int = 0
    flagged: bool = False
    layer_scores: dict[str, int] = field(default_factory=dict)
    details: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CanaryToken:
    token: str
    position: str  # prefix|suffix|both


class InjectionDetector:
    def __init__(self, patterns: list | None = None):
        self._patterns = [
            (re.compile(p, re.IGNORECASE), score, category)
            for p, score, category in (patterns or INJECTION_PATTERNS)
        ]

    def scan(
        self,
        text: str,
        canary: CanaryToken | None = None,
        llm_score: int | None = None,
    ) -> ScanResult:
        result = ScanResult()

        l1 = self._layer1_regex(text)
        result.layer_scores["regex"] = l1

        l2 = self._layer2_canary(text, canary) if canary else 0
        result.layer_scores["canary"] = l2

        l3 = self._layer3_structural(text)
        result.layer_scores["structural"] = l3

        l4 = llm_score if llm_score is not None else 0
        result.layer_scores["llm_classifier"] = l4

        weights = {"regex": 0.30, "canary": 0.30, "structural": 0.20, "llm_classifier": 0.20}
        weighted = sum(result.layer_scores[k] * weights[k] for k in weights)
        result.score = min(int(weighted), 100)

        result.flagged = result.score >= 50

        return result

    def _layer1_regex(self, text: str) -> int:
        max_score = 0
        for pattern, score, category in self._patterns:
            matches = pattern.findall(text)
            if matches:
                max_score = max(max_score, score)
        return max_score

    def _layer2_canary(self, text: str, canary: CanaryToken) -> int:
        if canary.position in ("prefix", "both"):
            if not text.startswith(canary.token):
                return 90
        if canary.position in ("suffix", "both"):
            if not text.rstrip().endswith(canary.token):
                return 90

        if canary.token not in text:
            return 95

        count = text.count(canary.token)
        expected = 2 if canary.position == "both" else 1
        if count != expected:
            return 70

        return 0

    def _layer3_structural(self, text: str) -> int:
        max_score = 0
        text_lower = text.lower()

        for delim in STRUCTURAL_DELIMITERS:
            if delim.lower() in text_lower:
                max_score = max(max_score, 80)

        boundary_patterns = [
            (r"```\s*system", 70),
            (r"\n-{3,}\s*\n.*(?:instruction|system|prompt)", 65),
            (r"<\|(?:im_start|im_end|system|user|assistant)\|>", 85),
            (r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", 85),
        ]
        for bp, score in boundary_patterns:
            if re.search(bp, text, re.IGNORECASE):
                max_score = max(max_score, score)

        return max_score

    @staticmethod
    def generate_canary(position: str = "prefix") -> CanaryToken:
        token = f"<<CANARY:{secrets.token_hex(8)}>>"
        return CanaryToken(token=token, position=position)

    @staticmethod
    def wrap_untrusted(text: str, canary: CanaryToken | None = None) -> str:
        inner = text
        if canary:
            if canary.position in ("prefix", "both"):
                inner = canary.token + inner
            if canary.position in ("suffix", "both"):
                inner = inner + canary.token
        return f"<untrusted_document>\n{inner}\n</untrusted_document>"
