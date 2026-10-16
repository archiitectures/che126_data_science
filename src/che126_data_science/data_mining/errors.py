"""Recognize operational source failures without swallowing programming errors."""

from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile


def source_failure(exc):
    if isinstance(exc, (OSError, ValueError, RuntimeError, ParseError, BadZipFile)):
        return True
    # Optional SDKs remain lazy. Match their base exception, not arbitrary errors.
    return any(
        (cls.__module__, cls.__name__)
        in {
            ("google.api_core.exceptions", "GoogleAPICallError"),
            ("google.auth.exceptions", "GoogleAuthError"),
            ("pymupdf", "FileDataError"),
            ("pymupdf", "EmptyFileError"),
            ("lxml.etree", "XMLSyntaxError"),
            ("openpyxl.utils.exceptions", "InvalidFileException"),
        }
        for cls in type(exc).__mro__
    )
