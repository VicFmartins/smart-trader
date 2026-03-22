from __future__ import annotations

from datetime import UTC, datetime, time as dt_time
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError, TradeValidationError
from app.models.import_job import ImportJob
from app.models.setup import Setup
from app.models.trade import Trade
from app.models.trading_enums import AssetClass, ImportJobStatus, OperationType, TradeAsset, TradeSourceType, TradeStatus
from app.repositories.pagination import PagedResult
from app.repositories.trades import TradeRepository
from app.schemas.common import PaginationParams
from app.schemas.trade import TradeCreate, TradeListParams, TradeUpdate


POINT_VALUE_BY_ASSET = {
    TradeAsset.WIN: Decimal("0.20"),
    TradeAsset.WDO: Decimal("10.00"),
}


class TradeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trades = TradeRepository(db)

    def create_trade(self, payload: TradeCreate) -> Trade:
        values = self._build_trade_values(payload.model_dump())
        trade = Trade(**values)
        return self.trades.create(trade)

    def create_trades_bulk(self, payloads: list[TradeCreate]) -> tuple[list[Trade], str | None]:
        if not payloads:
            raise TradeValidationError("At least one trade is required for bulk creation.")

        values_list = [self._build_trade_values(payload.model_dump()) for payload in payloads]
        source_types = {TradeSourceType(values["source_type"]) for values in values_list}
        import_batch_ids = {str(values["import_batch_id"]) for values in values_list if values["import_batch_id"] is not None}

        if len(import_batch_ids) > 1:
            raise TradeValidationError("Bulk trade creation supports only one import batch at a time.")
        if source_types == {TradeSourceType.PDF_IMPORT} and not import_batch_ids:
            raise TradeValidationError("PDF import trades must include an import batch id.")
        if TradeSourceType.PDF_IMPORT in source_types and TradeSourceType.MANUAL in source_types:
            raise TradeValidationError("Bulk trade creation cannot mix manual and PDF import trades.")

        import_batch_id = next(iter(import_batch_ids), None)
        import_job = self._get_import_job_for_confirmation(import_batch_id=import_batch_id) if import_batch_id else None
        if import_job is not None and len(values_list) > import_job.total_trades:
            raise TradeValidationError("The number of reviewed trades exceeds the total trades registered for the import batch.")

        trades = [Trade(**values) for values in values_list]
        try:
            self.db.add_all(trades)
            if import_job is not None:
                import_job.imported_trades = len(trades)
                import_job.rejected_trades = max(import_job.total_trades - len(trades), 0)
                import_job.status = ImportJobStatus.COMPLETED if import_job.rejected_trades == 0 else ImportJobStatus.PARTIAL
                import_job.finished_at = datetime.now(UTC)
                self.db.add(import_job)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        for trade in trades:
            self.db.refresh(trade)
        return trades, import_batch_id

    def get_trade(self, trade_id: int) -> Trade:
        trade = self.trades.get_by_id(trade_id)
        if trade is None:
            raise ResourceNotFoundError(f"Trade not found: {trade_id}")
        return trade

    def update_trade(self, trade_id: int, payload: TradeUpdate) -> Trade:
        trade = self.get_trade(trade_id)
        incoming = payload.model_dump(exclude_unset=True)
        derived_gross_inputs = {"asset", "operation_type", "quantity", "entry_price", "exit_price"}
        merged = {
            "trade_date": trade.trade_date,
            "asset": trade.asset,
            "asset_class": trade.asset_class,
            "operation_type": trade.operation_type,
            "status": trade.status,
            "quantity": trade.quantity,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "gross_result": trade.gross_result,
            "fees": trade.fees,
            "net_result": trade.net_result,
            "broker": trade.broker,
            "setup_id": trade.setup_id,
            "source_type": trade.source_type,
            "imported_file_name": trade.imported_file_name,
            "import_batch_id": trade.import_batch_id,
            "trade_time": trade.trade_time,
            "contract_code": trade.contract_code,
            "notes": trade.notes,
            "confidence_score": trade.confidence_score,
        }
        merged.update(incoming)
        if "gross_result" not in incoming and derived_gross_inputs.intersection(incoming):
            merged["gross_result"] = None
        if "net_result" not in incoming and (derived_gross_inputs.intersection(incoming) or "fees" in incoming):
            merged["net_result"] = None
        values = self._build_trade_values(merged)

        for field, value in values.items():
            setattr(trade, field, value)
        return self.trades.save(trade)

    def delete_trade(self, trade_id: int) -> None:
        trade = self.get_trade(trade_id)
        self.trades.delete(trade)

    def list_trades(
        self,
        *,
        pagination: PaginationParams,
        filters: TradeListParams,
    ) -> PagedResult[Trade]:
        normalized_filters = TradeListParams(
            date_from=filters.date_from,
            date_to=filters.date_to,
            asset=filters.asset,
            broker=filters.broker.strip().upper() if filters.broker else None,
            setup_id=filters.setup_id,
            source_type=filters.source_type,
            status=filters.status,
            result_filter=filters.result_filter,
            sort_by=filters.sort_by,
            sort_direction=filters.sort_direction,
        )
        return self.trades.list_trades(pagination=pagination, filters=normalized_filters)

    def _build_trade_values(self, values: dict[str, object]) -> dict[str, object]:
        asset = TradeAsset(values["asset"])
        asset_class = AssetClass(values["asset_class"])
        operation_type = OperationType(values["operation_type"])
        status = TradeStatus(values.get("status") or TradeStatus.CLOSED)
        source_type = TradeSourceType(values["source_type"])

        quantity = int(values["quantity"])
        entry_price = self._as_decimal(values["entry_price"], "entry_price")
        exit_price = self._as_optional_decimal(values.get("exit_price"), "exit_price")
        gross_result = self._as_optional_decimal(values.get("gross_result"), "gross_result")
        fees = self._as_decimal(values.get("fees", Decimal("0.00")), "fees")
        confidence_score = values.get("confidence_score")

        broker = self._normalize_required_string(values.get("broker"), "broker").upper()
        imported_file_name = self._normalize_optional_string(values.get("imported_file_name"))
        import_batch_id = self._normalize_optional_string(values.get("import_batch_id"))
        trade_time = self._parse_trade_time(values.get("trade_time"))
        contract_code = self._normalize_optional_string(values.get("contract_code"))
        notes = self._normalize_optional_string(values.get("notes"))
        setup_id = values.get("setup_id")

        self._validate_asset_mapping(asset, asset_class)
        self._validate_source_fields(
            source_type=source_type,
            imported_file_name=imported_file_name,
            import_batch_id=import_batch_id,
            confidence_score=confidence_score,
        )
        self._validate_setup(setup_id=setup_id, asset_class=asset_class)
        self._validate_import_job(import_batch_id=import_batch_id)

        if gross_result is None and exit_price is not None:
            gross_result = self._calculate_gross_result(
                asset=asset,
                operation_type=operation_type,
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=quantity,
            )

        net_result = self._calculate_net_result(gross_result=gross_result, fees=fees)

        if status == TradeStatus.CLOSED:
            if exit_price is None:
                raise TradeValidationError("Closed trades require an exit_price.")
            if gross_result is None:
                raise TradeValidationError("Closed trades require a gross_result or enough data to calculate it.")
            if net_result is None:
                raise TradeValidationError("Closed trades require a net_result or enough data to calculate it.")

        if status == TradeStatus.DRAFT:
            gross_result = gross_result if exit_price is not None else None
            net_result = net_result if gross_result is not None else None

        return {
            "trade_date": values["trade_date"],
            "asset": asset,
            "asset_class": asset_class,
            "operation_type": operation_type,
            "status": status,
            "quantity": quantity,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "gross_result": gross_result,
            "fees": fees,
            "net_result": net_result,
            "broker": broker,
            "setup_id": setup_id,
            "source_type": source_type,
            "imported_file_name": imported_file_name,
            "import_batch_id": import_batch_id,
            "trade_time": trade_time,
            "contract_code": contract_code,
            "notes": notes,
            "confidence_score": confidence_score,
        }

    def _validate_asset_mapping(self, asset: TradeAsset, asset_class: AssetClass) -> None:
        expected_asset_class = {
            TradeAsset.WIN: AssetClass.MINI_INDEX,
            TradeAsset.WDO: AssetClass.MINI_DOLLAR,
        }[asset]
        if asset_class != expected_asset_class:
            raise TradeValidationError("Asset class does not match the selected asset.")

    def _validate_source_fields(
        self,
        *,
        source_type: TradeSourceType,
        imported_file_name: str | None,
        import_batch_id: str | None,
        confidence_score: float | None,
    ) -> None:
        if source_type == TradeSourceType.PDF_IMPORT:
            if not imported_file_name:
                raise TradeValidationError("Imported trades must include the source file name.")
            if not import_batch_id:
                raise TradeValidationError("Imported trades must include the import batch id.")
        else:
            if imported_file_name is not None:
                raise TradeValidationError("Manual trades cannot carry an imported file name.")
            if import_batch_id is not None:
                raise TradeValidationError("Manual trades cannot carry an import batch id.")
            if confidence_score is not None:
                raise TradeValidationError("Manual trades cannot carry a confidence score.")

    def _validate_setup(self, *, setup_id: object, asset_class: AssetClass) -> None:
        if setup_id is None:
            return
        setup = self.db.get(Setup, int(setup_id))
        if setup is None:
            raise ResourceNotFoundError(f"Setup not found: {setup_id}")
        if setup.asset_class_scope is not None and setup.asset_class_scope != asset_class:
            raise TradeValidationError("The selected setup is not compatible with the trade asset class.")

    def _validate_import_job(self, *, import_batch_id: str | None) -> None:
        if import_batch_id is None:
            return
        import_job = self.db.execute(select(ImportJob).where(ImportJob.batch_id == import_batch_id)).scalar_one_or_none()
        if import_job is None:
            raise ResourceNotFoundError(f"Import job not found for batch id: {import_batch_id}")

    def _get_import_job_for_confirmation(self, *, import_batch_id: str) -> ImportJob:
        import_job = self.db.execute(select(ImportJob).where(ImportJob.batch_id == import_batch_id)).scalar_one_or_none()
        if import_job is None:
            raise ResourceNotFoundError(f"Import job not found for batch id: {import_batch_id}")
        if import_job.source_type != TradeSourceType.PDF_IMPORT:
            raise TradeValidationError("The import batch is not associated with a PDF import job.")
        if import_job.imported_trades > 0 or import_job.status in {ImportJobStatus.COMPLETED, ImportJobStatus.PARTIAL}:
            raise TradeValidationError("This PDF import batch has already been confirmed.")
        return import_job

    def _calculate_gross_result(
        self,
        *,
        asset: TradeAsset,
        operation_type: OperationType,
        entry_price: Decimal,
        exit_price: Decimal,
        quantity: int,
    ) -> Decimal:
        price_delta = exit_price - entry_price
        if operation_type == OperationType.SELL:
            price_delta = entry_price - exit_price
        gross = price_delta * Decimal(quantity) * POINT_VALUE_BY_ASSET[asset]
        return gross.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calculate_net_result(self, *, gross_result: Decimal | None, fees: Decimal) -> Decimal | None:
        if gross_result is None:
            return None
        return (gross_result - fees).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _as_decimal(self, value: object, field_name: str) -> Decimal:
        decimal_value = self._as_optional_decimal(value, field_name)
        if decimal_value is None:
            raise TradeValidationError(f"{field_name} is required.")
        return decimal_value

    def _as_optional_decimal(self, value: object, field_name: str) -> Decimal | None:
        if value is None:
            return None
        decimal_value = Decimal(str(value))
        if field_name in {"entry_price", "exit_price"} and decimal_value <= 0:
            raise TradeValidationError(f"{field_name} must be greater than zero.")
        if field_name == "fees" and decimal_value < 0:
            raise TradeValidationError("fees must be zero or greater.")
        return decimal_value

    def _normalize_required_string(self, value: object, field_name: str) -> str:
        cleaned = self._normalize_optional_string(value)
        if not cleaned:
            raise TradeValidationError(f"{field_name} is required.")
        return cleaned

    @staticmethod
    def _parse_trade_time(value: object) -> dt_time | None:
        if value is None:
            return None
        if isinstance(value, dt_time):
            return value
        cleaned = str(value).strip()
        if not cleaned:
            return None
        try:
            parts = cleaned.split(":")
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            s = int(parts[2]) if len(parts) > 2 else 0
            return dt_time(h, m, s)
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _normalize_optional_string(value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None
