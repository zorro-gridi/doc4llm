"""
Custom exceptions for the document extraction tool module.

This module defines all custom exceptions used by the markdown document
extractor for proper error handling and graceful degradation.
"""


class DocExtractorError(Exception):
    """Base exception for all document extractor errors.

    All custom exceptions in the tool module inherit from this base class,
    allowing for consistent exception handling patterns.
    """
    pass


class DocumentNotFoundError(DocExtractorError):
    """Raised when a document file cannot be found.

    This exception is raised when:
    - The specified document path does not exist
    - The docContent.md file is missing from a document directory
    - The document structure is invalid

    Attributes:
        title: The title of the document that was not found
        path: The path that was attempted to be accessed
    """

    def __init__(self, title: str, path: str | None = None):
        self.title = title
        self.path = path
        message = f"Document not found: '{title}'"
        if path:
            message += f" (expected at: {path})"
        super().__init__(message)


class InvalidTitleError(DocExtractorError):
    """Raised when a document title is invalid or cannot be processed.

    This exception is raised when:
    - The title is None or empty
    - The title contains invalid characters
    - The title format is not compatible with the document structure

    Attributes:
        title: The invalid title that caused the error
        reason: Detailed explanation of why the title is invalid
    """

    def __init__(self, title: str, reason: str | None = None):
        self.title = title
        self.reason = reason
        message = f"Invalid title: '{title}'"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class BaseDirectoryNotFoundError(DocExtractorError):
    """Raised when the documentation base directory does not exist.

    This exception is raised when the configured or specified documentation
    output directory cannot be found or accessed.

    Attributes:
        base_dir: The base directory path that was not found
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        super().__init__(f"Documentation base directory not found: '{base_dir}'")


class NoDocumentsFoundError(DocExtractorError):
    """Raised when no documents are found in the documentation structure.

    This exception is raised when:
    - The documentation directory exists but contains no documents
    - No documents match the search criteria
    - The document structure is empty or malformed

    Attributes:
        base_dir: The base directory that was searched
        criteria: Optional search criteria that yielded no results
    """

    def __init__(self, base_dir: str, criteria: str | None = None):
        self.base_dir = base_dir
        self.criteria = criteria
        message = f"No documents found in: '{base_dir}'"
        if criteria:
            message += f" matching criteria: {criteria}"
        super().__init__(message)


class ConfigurationError(DocExtractorError):
    """Raised when there is a configuration-related error.

    This exception is raised when:
    - Invalid configuration values are provided
    - Required configuration is missing
    - Configuration conflicts exist

    Attributes:
        parameter: The configuration parameter that caused the error
        reason: Detailed explanation of the configuration issue
    """

    def __init__(self, parameter: str, reason: str | None = None):
        self.parameter = parameter
        self.reason = reason
        message = f"Configuration error for parameter: '{parameter}'"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class SingleFileNotFoundError(DocExtractorError):
    """Raised when a single file specified in single file mode is not found.

    This exception is raised when:
    - The file path specified in single_file_path does not exist
    - The file is not a .md file

    Attributes:
        file_path: The file path that was not found
        reason: Detailed explanation of why the file is invalid
    """

    def __init__(self, file_path: str, reason: str | None = None):
        self.file_path = file_path
        self.reason = reason
        message = f"Single file not found: '{file_path}'"
        if reason:
            message += f" - {reason}"
        super().__init__(message)
