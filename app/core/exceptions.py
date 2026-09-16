"""Transport-agnostic application errors.

Services raise these so business logic stays free of HTTP concerns; a single
exception handler in `app.main` maps them onto status codes.
"""


class AppError(Exception):
    # Status codes are plain integers so this module does not track renames of
    # Starlette's status constants.
    status_code = 400
    default_message = "Request could not be processed."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    default_message = "Resource not found."


class ValidationError(AppError):
    status_code = 422
    default_message = "The submitted data is invalid."


class ConflictError(AppError):
    status_code = 409
    default_message = "Resource already exists."


class AuthenticationError(AppError):
    status_code = 401
    default_message = "Authentication required."


class PermissionDeniedError(AppError):
    status_code = 403
    default_message = "You do not have access to this resource."


class QuotaExceededError(AppError):
    status_code = 429
    default_message = "Daily usage limit reached. Try again tomorrow."


class PayloadTooLargeError(AppError):
    status_code = 413
    default_message = "Upload is too large."


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    default_message = "This file type is not supported."


class UpstreamServiceError(AppError):
    status_code = 502
    default_message = "An upstream service is unavailable."
