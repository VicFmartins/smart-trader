class ApplicationError(Exception):
    def __init__(self, message: str, *, error_code: str = "application_error") -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ResourceNotFoundError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="resource_not_found")


class ETLInputError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="etl_input_error")


class ETLValidationError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="etl_validation_error")


class UploadTooLargeError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="upload_too_large")


class S3OperationError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="s3_operation_error")


class AuthenticationError(ApplicationError):
    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(message, error_code="authentication_error")


class AuthorizationError(ApplicationError):
    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message, error_code="authorization_error")


class TradeValidationError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="trade_validation_error")


class DocumentImportError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="document_import_error")


class InvalidLLMResponseError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="invalid_llm_response")


class ServiceUnavailableError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="service_unavailable")
