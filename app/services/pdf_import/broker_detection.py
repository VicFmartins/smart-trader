from __future__ import annotations

from app.schemas.pdf_import import BrokerDetectionResult


BROKER_PATTERNS: dict[str, tuple[str, ...]] = {
    "XP": ("xp investimentos", "xp invest", "xp cctvm", "xpi"),
    "CLEAR": ("clear corretora", "clear investimentos", "clear cor"),
    "RICO": ("rico investimentos", "rico"),
    "BTG": ("btg pactual", "btg"),
    "INTER": ("banco inter", "inter d.t.v.m", "inter investimentos"),
    "NUINVEST": ("nuinvest", "easynvest"),
    "MODAL": ("modalmais", "modal mais", "modal d.t.v.m"),
}


class BrokerDetector:
    def detect(self, *, filename: str, extracted_text: str) -> BrokerDetectionResult:
        filename_lower = filename.lower()
        text_lower = extracted_text.lower()

        for broker, patterns in BROKER_PATTERNS.items():
            for pattern in patterns:
                if pattern in filename_lower:
                    return BrokerDetectionResult(
                        broker=broker,
                        confidence=0.95,
                        strategy="filename",
                        evidence=[pattern],
                    )

        for broker, patterns in BROKER_PATTERNS.items():
            matches = [pattern for pattern in patterns if pattern in text_lower]
            if matches:
                confidence = min(0.9, 0.45 + (0.15 * len(matches)))
                return BrokerDetectionResult(
                    broker=broker,
                    confidence=confidence,
                    strategy="text",
                    evidence=matches,
                )

        return BrokerDetectionResult(
            broker=None,
            confidence=0.0,
            strategy="unknown",
            evidence=[],
        )
