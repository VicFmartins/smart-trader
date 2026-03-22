from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import ApplicationError
from app.etl.contracts import ETLFileSummary
from app.etl.enrich.asset_enricher import enrich_assets
from app.etl.extract.file_reader import FileReader
from app.etl.extract.xp_bundle_parser import XPBundleParser
from app.etl.load.loader import PortfolioLoader
from app.etl.transform.classifier import apply_asset_classification
from app.etl.transform.normalizer import normalize_portfolio_frame
from app.services.storage_service import RawFileStorageService
from app.services.accepted_mapping_service import AcceptedMappingService
from app.utils.files import write_dataframe_snapshot, write_dataframe_to_csv


logger = logging.getLogger(__name__)


class PortfolioETLPipeline:
    def __init__(self, db: Session) -> None:
        self.db = db
        accepted_mappings = AcceptedMappingService(db)
        self.reader = FileReader(mapping_resolver=lambda layout_signature: accepted_mappings.get_preferred_mappings(layout_signature=layout_signature))
        self.xp_bundle_parser = XPBundleParser()
        self.loader = PortfolioLoader(db)
        self.storage = RawFileStorageService()

    def run(
        self,
        source_path: Path | None = None,
        *,
        source_type: str = "local",
        s3_bucket_name: str | None = None,
        s3_key: str | None = None,
        s3_prefix: str | None = None,
    ) -> ETLFileSummary:
        source_label, raw_reference, raw_file_path = self._resolve_source(
            source_path=source_path,
            source_type=source_type,
            s3_bucket_name=s3_bucket_name,
            s3_key=s3_key,
            s3_prefix=s3_prefix,
        )

        logger.info("Starting ETL pipeline for %s", source_label)
        try:
            if raw_file_path.is_dir():
                dataframe = self.xp_bundle_parser.parse_directory(raw_file_path)
                parser_name = dataframe.attrs.get("parser_name", "xp_bundle_parser")
                parser_failures = dataframe.attrs.get("parser_failures", [])
                raw_artifact_path = write_dataframe_snapshot(dataframe, self.storage.settings.raw_data_dir, "xp_bundle_raw")
                logger.info("Using parser %s for directory source %s", parser_name, source_label)
                if parser_failures:
                    logger.warning("XP bundle parser had partial failures for %s: %s", source_label, parser_failures)
            else:
                dataframe = self.reader.read(raw_file_path)
                parser_name = dataframe.attrs.get("parser_name", "generic_reader")
                raw_artifact_path = raw_reference
                logger.info("Using parser %s for %s", parser_name, source_label)
            review_decision = dataframe.attrs.get("review_decision", {})
            detection_confidence = dataframe.attrs.get("detection_confidence")
            review_required = bool(dataframe.attrs.get("review_required", False))
            review_reasons = list(review_decision.get("reasons", ()))
            layout_signature = dataframe.attrs.get("layout_signature")
            detected_columns = tuple(str(column) for column in dataframe.attrs.get("detected_columns", tuple(dataframe.columns)))
            applied_mappings = tuple(dict(item) for item in dataframe.attrs.get("column_mapping", ()))
            structure_detection = dataframe.attrs.get("structure_detection")
            transformed = normalize_portfolio_frame(dataframe)
            normalization_review_required = bool(transformed.attrs.get("review_required", False))
            normalization_review_reasons = list(transformed.attrs.get("review_reasons", ()))
            if normalization_review_required:
                review_required = True
            if normalization_review_reasons:
                review_reasons.extend(normalization_review_reasons)
                if detection_confidence is None:
                    detection_confidence = 60.0
                else:
                    detection_confidence = min(float(detection_confidence), 60.0)
            classified = apply_asset_classification(transformed)
            enriched = enrich_assets(classified)
            processed_file_path = write_dataframe_to_csv(enriched)
            load_stats = self.loader.load(enriched)
            rows_skipped = int(transformed.attrs.get("rows_skipped", 0))
            validation_summary = transformed.attrs.get("validation_summary", {})
            if validation_summary:
                logger.info("Validation summary for %s: %s", source_label, validation_summary)
            logger.info(
                "Finished ETL pipeline for %s with %s processed rows and %s skipped rows.",
                source_label,
                len(enriched),
                rows_skipped,
            )

            return ETLFileSummary(
                source_file=source_label,
                raw_file=raw_artifact_path,
                processed_file=processed_file_path,
                rows_processed=int(len(enriched)),
                rows_skipped=rows_skipped,
                detection_confidence=detection_confidence,
                review_required=review_required,
                review_reasons=tuple(dict.fromkeys(review_reasons)),
                parser_name=parser_name,
                layout_signature=str(layout_signature) if layout_signature else None,
                detected_columns=detected_columns,
                applied_mappings=applied_mappings,
                structure_detection=dict(structure_detection) if isinstance(structure_detection, dict) else None,
                **load_stats,
            )
        except ApplicationError:
            logger.warning("ETL pipeline failed for %s with an application error.", source_label)
            raise
        except Exception:
            logger.exception("ETL pipeline failed for %s", source_label)
            raise

    def _resolve_source(
        self,
        *,
        source_path: Path | None,
        source_type: str,
        s3_bucket_name: str | None,
        s3_key: str | None,
        s3_prefix: str | None,
    ) -> tuple[str, str, Path]:
        if source_type == "s3":
            source_uri, local_path = self.storage.fetch_s3_file_to_raw(
                s3_key=s3_key,
                s3_prefix=s3_prefix,
                bucket_name=s3_bucket_name,
            )
            return source_uri, source_uri, local_path

        if source_path is None:
            raise ValueError("source_path is required when source_type='local'")

        if source_path.is_dir():
            return str(source_path), str(source_path), source_path

        raw_reference, processing_path = self.storage.store_raw_file(source_path)
        return str(source_path), raw_reference, processing_path
