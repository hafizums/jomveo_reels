class AppError(Exception):
    status_code = 500
    code = "app_error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or "An application error occurred."
        super().__init__(self.message)


class ConfigurationError(AppError):
    code = "configuration_error"


class AuthRequiredError(AppError):
    status_code = 401
    code = "auth_required"


class AuthForbiddenError(AppError):
    status_code = 403
    code = "auth_forbidden"


class ProjectNotFoundError(AppError):
    status_code = 404
    code = "project_not_found"


class BillingError(AppError):
    code = "billing_error"


class BillingInsufficientCreditsError(BillingError):
    status_code = 402
    code = "insufficient_credits"


class QuotaExceededError(AppError):
    status_code = 429
    code = "quota_exceeded"


class ProviderError(AppError):
    status_code = 502
    code = "provider_error"


class ProviderAuthError(ProviderError):
    code = "provider_auth_error"


class ProviderForbiddenError(ProviderError):
    code = "provider_forbidden_error"


class ProviderTimeoutError(ProviderError):
    status_code = 504
    code = "provider_timeout_error"


class ProviderBadResponseError(ProviderError):
    code = "provider_bad_response_error"


class MediaProcessingError(AppError):
    code = "media_processing_error"


class ValidationAppError(AppError):
    status_code = 400
    code = "validation_error"


class JobNotFoundError(AppError):
    status_code = 404
    code = "job_not_found"


class StorageError(AppError):
    code = "storage_error"


class UnsafePathError(StorageError):
    status_code = 400
    code = "unsafe_path"


class UploadValidationError(ValidationAppError):
    code = "upload_validation_error"


class RemoteDownloadError(AppError):
    status_code = 502
    code = "remote_download_error"


class UnsafeRemoteURLError(ValidationAppError):
    code = "unsafe_remote_url"


class MediaValidationError(ValidationAppError):
    code = "media_validation_error"
