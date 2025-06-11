"""
Custom exception classes for the AudioBook Converter application.
"""

class AudioBookException(Exception):
    """Base exception class for AudioBook Converter."""
    
    def __init__(self, detail: str, status_code: int = 400, error_code: str = "AUDIOBOOK_ERROR"):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(detail)

class FileProcessingError(AudioBookException):
    """Exception raised when file processing fails."""
    
    def __init__(self, detail: str, file_type: str = None):
        error_code = f"FILE_PROCESSING_ERROR_{file_type.upper()}" if file_type else "FILE_PROCESSING_ERROR"
        super().__init__(detail, status_code=422, error_code=error_code)

class TextExtractionError(AudioBookException):
    """Exception raised when text extraction fails."""
    
    def __init__(self, detail: str):
        super().__init__(detail, status_code=422, error_code="TEXT_EXTRACTION_ERROR")

class TTSError(AudioBookException):
    """Exception raised when TTS conversion fails."""
    
    def __init__(self, detail: str):
        super().__init__(detail, status_code=422, error_code="TTS_ERROR")

class AIProcessingError(AudioBookException):
    """Exception raised when AI processing fails."""
    
    def __init__(self, detail: str, service: str = "unknown"):
        error_code = f"AI_PROCESSING_ERROR_{service.upper()}"
        super().__init__(detail, status_code=422, error_code=error_code)

class BookNotFoundError(AudioBookException):
    """Exception raised when a book is not found."""
    
    def __init__(self, book_id: str):
        detail = f"Book with ID {book_id} not found"
        super().__init__(detail, status_code=404, error_code="BOOK_NOT_FOUND")

class ConversionJobNotFoundError(AudioBookException):
    """Exception raised when a conversion job is not found."""
    
    def __init__(self, job_id: str):
        detail = f"Conversion job with ID {job_id} not found"
        super().__init__(detail, status_code=404, error_code="CONVERSION_JOB_NOT_FOUND")

class UserNotFoundError(AudioBookException):
    """Exception raised when a user is not found."""
    
    def __init__(self, user_id: str = None):
        detail = f"User {user_id} not found" if user_id else "User not found"
        super().__init__(detail, status_code=404, error_code="USER_NOT_FOUND")

class AuthenticationError(AudioBookException):
    """Exception raised when authentication fails."""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(detail, status_code=401, error_code="AUTHENTICATION_ERROR")

class AuthorizationError(AudioBookException):
    """Exception raised when authorization fails."""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(detail, status_code=403, error_code="AUTHORIZATION_ERROR")

class FileTooLargeError(AudioBookException):
    """Exception raised when uploaded file is too large."""
    
    def __init__(self, max_size: int):
        detail = f"File size exceeds maximum allowed size of {max_size} bytes"
        super().__init__(detail, status_code=413, error_code="FILE_TOO_LARGE")

class UnsupportedFileTypeError(AudioBookException):
    """Exception raised when file type is not supported."""
    
    def __init__(self, file_type: str):
        detail = f"File type '{file_type}' is not supported"
        super().__init__(detail, status_code=422, error_code="UNSUPPORTED_FILE_TYPE")

class RateLimitExceededError(AudioBookException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(detail, status_code=429, error_code="RATE_LIMIT_EXCEEDED") 