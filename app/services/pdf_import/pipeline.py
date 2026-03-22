from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings
from app.core.exceptions import DocumentImportError
from app.schemas.pdf_import import (
    LLMTradeExtractionPayload,
    OllamaInferenceMetadata,
    PDFImportReviewPayload,
    TradeReviewWarning,
)
from app.services.pdf_import.broker_detection import BrokerDetector
from app.services.pdf_import.extraction import PDFTextExtractor
from app.services.pdf_import.json_parser import StructuredOutputParser
from app.services.pdf_import.ollama_client import LLMChatClient, OllamaClient
from app.services.pdf_import.parsers import BrokerParserContext, BrokerTradeNoteParserRegistry, GenericOllamaBrokerParser
from app.services.pdf_import.validation import TradeExtractionNormalizer


class PDFImportReviewService:
    def __init__(
        self,
        *,
        text_extractor: PDFTextExtractor,
        broker_detector: BrokerDetector,
        parser_registry: BrokerTradeNoteParserRegistry,
        ollama_client: LLMChatClient,
        normalizer: TradeExtractionNormalizer,
    ) -> None:
        self.text_extractor = text_extractor
        self.broker_detector = broker_detector
        self.parser_registry = parser_registry
        self.ollama_client = ollama_client
        self.normalizer = normalizer

    @classmethod
    def from_settings(cls) -> "PDFImportReviewService":
        settings = get_settings()

        if settings.llm_provider == "gemini":
            from app.services.pdf_import.gemini_client import GeminiClient
            llm_client: LLMChatClient = GeminiClient(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                timeout_seconds=settings.gemini_timeout_seconds,
            )
        else:
            llm_client = OllamaClient(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                timeout_seconds=settings.ollama_timeout_seconds,
            )

        output_parser = StructuredOutputParser()
        default_parser = GenericOllamaBrokerParser(ollama_client=llm_client, output_parser=output_parser)
        return cls(
            text_extractor=PDFTextExtractor(
                max_pages=settings.pdf_import_max_pages,
                max_chars=settings.pdf_import_max_chars,
            ),
            broker_detector=BrokerDetector(),
            parser_registry=BrokerTradeNoteParserRegistry(default_parser=default_parser),
            ollama_client=llm_client,
            normalizer=TradeExtractionNormalizer(),
        )

    def review_pdf_bytes(self, *, filename: str, file_bytes: bytes, import_batch_id: str | None = None) -> PDFImportReviewPayload:
        self._validate_pdf_filename(filename)
        extraction = self.text_extractor.extract(file_bytes)
        broker_detection = self.broker_detector.detect(filename=filename, extracted_text=extraction.combined_text)
        parser = self.parser_registry.resolve(broker_detection.broker)

        response, parsed_output, fallback_used = parser.parse(
            BrokerParserContext(
                filename=filename,
                extracted_text=extraction.combined_text,
                broker_detection=broker_detection,
            )
        )

        normalized = self.normalizer.normalize(
            filename=filename,
            broker_detection=broker_detection,
            payload=parsed_output.payload or LLMTradeExtractionPayload(),
            import_batch_id=import_batch_id,
        )
        warnings = list(normalized.warnings)
        warnings.extend(TradeReviewWarning(code="llm_warning", message=warning) for warning in parsed_output.warnings)
        if extraction.metadata.text_truncated:
            warnings.append(
                self._warning(code="truncated_text", message="Extracted text was truncated before the LLM request.")
            )
        validation_errors = list(parsed_output.errors)
        if not normalized.trades:
            warnings.append(self._warning(code="no_trades_extracted", message="No trades were extracted from the PDF."))

        return PDFImportReviewPayload(
            filename=filename,
            broker_detection=broker_detection,
            normalized_broker=normalized.normalized_broker,
            normalized_trade_date=normalized.normalized_trade_date,
            extraction=extraction.metadata,
            llm=OllamaInferenceMetadata(
                model=response.model,
                base_url=self.ollama_client.base_url,
                request_succeeded=True,
                json_valid=parsed_output.is_valid,
                fallback_used=fallback_used,
                raw_response=response.content,
            ),
            pages=extraction.pages,
            extracted_text=extraction.combined_text,
            trades=normalized.trades,
            warnings=warnings,
            validation_errors=validation_errors,
            raw_json=parsed_output.raw_json,
            review_required=(not parsed_output.is_valid)
            or bool(validation_errors)
            or bool(warnings)
            or any(not trade.ready_for_persistence for trade in normalized.trades),
        )

    @classmethod
    def process_uploaded_stream(
        cls,
        filename: str,
        file_stream: BinaryIO,
        import_batch_id: str | None = None,
    ) -> PDFImportReviewPayload:
        file_stream.seek(0)
        return cls.from_settings().review_pdf_bytes(
            filename=filename,
            file_bytes=file_stream.read(),
            import_batch_id=import_batch_id,
        )

    def _validate_pdf_filename(self, filename: str) -> None:
        cleaned_name = Path(filename or "").name
        if not cleaned_name:
            raise DocumentImportError("Uploaded PDF must include a valid filename.")
        if Path(cleaned_name).suffix.lower() != ".pdf":
            raise DocumentImportError("Only PDF uploads are supported for brokerage note review.")

    @staticmethod
    def _warning(*, code: str, message: str):
        from app.schemas.pdf_import import TradeReviewWarning

        return TradeReviewWarning(code=code, message=message)
