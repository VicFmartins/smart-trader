from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.schemas.pdf_import import BrokerDetectionResult, LLMTradeExtractionPayload
from app.core.exceptions import ServiceUnavailableError
from app.services.pdf_import.json_parser import ParsedStructuredOutput, StructuredOutputParser
from app.services.pdf_import.ollama_client import LLMChatClient, OllamaChatResult


@dataclass(frozen=True, slots=True)
class BrokerParserContext:
    filename: str
    extracted_text: str
    broker_detection: BrokerDetectionResult


class BrokerTradeNoteParser(ABC):
    @abstractmethod
    def parse(self, context: BrokerParserContext) -> tuple[OllamaChatResult, ParsedStructuredOutput[LLMTradeExtractionPayload], bool]:
        raise NotImplementedError


class GenericOllamaBrokerParser(BrokerTradeNoteParser):
    def __init__(self, *, ollama_client: LLMChatClient, output_parser: StructuredOutputParser) -> None:
        self.ollama_client = ollama_client
        self.output_parser = output_parser

    def parse(self, context: BrokerParserContext) -> tuple[OllamaChatResult, ParsedStructuredOutput[LLMTradeExtractionPayload], bool]:
        schema = self._build_schema()
        prompt = self._build_prompt(context=context, schema=schema)
        fallback_used = False
        try:
            response = self.ollama_client.chat_with_schema(prompt=prompt, schema=schema)
        except ServiceUnavailableError:
            response = self.ollama_client.chat(prompt=prompt)
            fallback_used = True
        parsed = self.output_parser.parse(response.content, LLMTradeExtractionPayload)

        if parsed.is_valid:
            return response, parsed, fallback_used

        repair_response = self.ollama_client.repair_json(invalid_response=response.content, schema=schema)
        repaired = self.output_parser.parse(repair_response.content, LLMTradeExtractionPayload)
        fallback_used = True
        return repair_response, repaired, fallback_used

    def _build_prompt(self, *, context: BrokerParserContext, schema: dict) -> str:
        detected_broker = context.broker_detection.broker or "unknown"
        return (
            "You extract only Brazilian B3 day-trade operations from brokerage note text.\n"
            "Focus only on WIN and WDO trades. Ignore equities, options, custody, summaries, taxes, and unrelated tables.\n"
            "If the note does not contain explicit WIN or WDO operations, return an empty trades array.\n"
            "Return only JSON that matches the schema exactly.\n"
            "If a field cannot be determined, use null.\n"
            "Use these enums exactly:\n"
            '- asset: "WIN" or "WDO"\n'
            '- asset_class: "WIN", "WDO", or "OTHER" when uncertain\n'
            '- operation_type: "BUY" if the trade was opened with a buy, "SELL" if opened with a sell\n'
            "- trade_time: use HH:MM:SS format for the OPENING time of the trade, otherwise null\n"
            "Each trade record represents one COMPLETED round-trip day-trade:\n"
            "- entry_price: the price at which the position was OPENED\n"
            "- exit_price: the price at which the position was CLOSED\n"
            "- gross_result: the gross profit or loss of this round trip (positive = profit, negative = loss)\n"
            "- fees: total brokerage fees and emoluments for this trade\n"
            "- net_result: gross_result minus fees\n"
            "If the document lists BUY and SELL operations separately, pair them into a single completed trade record.\n"
            "Prefer the consolidated day-trade summary table when available — it already provides paired results.\n"
            f"Detected broker hint: {detected_broker}\n"
            f"Filename: {context.filename}\n"
            "Document text:\n"
            f"{context.extracted_text}"
        )

    def _build_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "broker": {"type": ["string", "null"]},
                "document_date": {"type": ["string", "null"]},
                "notes": {"type": ["string", "null"]},
                "trades": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "trade_date": {"type": ["string", "null"]},
                            "asset": {"type": ["string", "null"], "enum": ["WIN", "WDO", None]},
                            "asset_class": {"type": ["string", "null"], "enum": ["WIN", "WDO", "OTHER", None]},
                            "operation_type": {"type": ["string", "null"], "enum": ["BUY", "SELL", None]},
                            "quantity": {"type": ["integer", "number", "string", "null"]},
                            "entry_price": {"type": ["number", "string", "null"]},
                            "exit_price": {"type": ["number", "string", "null"]},
                            "gross_result": {"type": ["number", "string", "null"]},
                            "fees": {"type": ["number", "string", "null"]},
                            "net_result": {"type": ["number", "string", "null"]},
                            "trade_time": {"type": ["string", "null"]},
                            "broker": {"type": ["string", "null"]},
                            "notes": {"type": ["string", "null"]},
                            "confidence_score": {"type": ["number", "string", "null"]},
                            "source_page": {"type": ["integer", "number", "string", "null"]},
                        },
                        "required": [
                            "trade_date",
                            "asset",
                            "asset_class",
                            "operation_type",
                            "quantity",
                            "entry_price",
                            "exit_price",
                            "gross_result",
                            "fees",
                            "net_result",
                            "trade_time",
                            "broker",
                            "notes",
                            "confidence_score",
                            "source_page",
                        ],
                        "additionalProperties": False,
                    },
                },
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["broker", "document_date", "notes", "trades", "warnings"],
            "additionalProperties": False,
        }


class BrokerTradeNoteParserRegistry:
    def __init__(self, *, default_parser: BrokerTradeNoteParser, broker_parsers: dict[str, BrokerTradeNoteParser] | None = None) -> None:
        self.default_parser = default_parser
        self.broker_parsers = {broker.upper(): parser for broker, parser in (broker_parsers or {}).items()}

    def resolve(self, broker: str | None) -> BrokerTradeNoteParser:
        if broker is None:
            return self.default_parser
        return self.broker_parsers.get(broker.upper(), self.default_parser)
