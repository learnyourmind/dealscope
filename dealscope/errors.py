"""Domain errors mapped to stable codes, HTTP statuses, and client-safe messages (spec §5.3).

Messages are fixed strings or contain only field names chosen by this code base. Never
interpolate exception text, user input, or upstream content into a message.
"""

from typing import Any, Dict, List, Optional


class DealScopeError(Exception):
    code = "INTERNAL_ERROR"
    status = 500
    message = "Something went wrong on our side. Please try again."
    retryable = True

    def __init__(self, message: Optional[str] = None, **details: Any):
        super().__init__(self.code)
        self.message = message or type(self).message
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        body = {"code": self.code, "message": self.message, "retryable": self.retryable}
        body.update(self.details)
        return body


class InvalidRequest(DealScopeError):
    code = "INVALID_REQUEST"
    status = 400
    message = "The request was not valid."
    retryable = False


class OutOfRange(DealScopeError):
    code = "OUT_OF_RANGE"
    status = 400
    message = "A value is outside the allowed range."
    retryable = False


class NotFound(DealScopeError):
    code = "NOT_FOUND"
    status = 404
    message = "That page does not exist."
    retryable = False


class MethodNotAllowed(DealScopeError):
    code = "METHOD_NOT_ALLOWED"
    status = 405
    message = "That method is not allowed here."
    retryable = False


class PropertyNotFound(DealScopeError):
    code = "PROPERTY_NOT_FOUND"
    status = 404
    message = "We couldn't find a matching property. Check the address and try again."
    retryable = False


class AmbiguousMatch(DealScopeError):
    code = "AMBIGUOUS_MATCH"
    status = 422
    message = "Several properties match that address. Choose the right one."
    retryable = False

    def __init__(self, candidates: List[Dict[str, str]]):
        super().__init__(candidates=candidates)


class InsufficientData(DealScopeError):
    code = "INSUFFICIENT_DATA"
    status = 422
    message = "We don't have enough property data to run an analysis."
    retryable = False


class ProviderTimeout(DealScopeError):
    code = "PROVIDER_TIMEOUT"
    status = 504
    message = "The property data source took too long to respond. Please try again."


class ProviderRateLimited(DealScopeError):
    code = "PROVIDER_RATE_LIMITED"
    status = 503
    message = "The property data source is limiting requests right now. Please try again later."


class ProviderUnavailable(DealScopeError):
    code = "PROVIDER_UNAVAILABLE"
    status = 502
    message = "The property data source is unavailable or returned unusable data. Please try again."


class RateLimited(DealScopeError):
    code = "RATE_LIMITED"
    status = 429
    message = "Too many requests. Please wait a moment and try again."
