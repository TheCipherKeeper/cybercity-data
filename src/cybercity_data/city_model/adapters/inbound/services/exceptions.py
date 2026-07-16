"""Application-level exception used by the service layer."""


class ApplicationError(Exception):
    """Any failure the CLI should present to the user instead of a traceback."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
