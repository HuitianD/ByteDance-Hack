"""User-safe diagnostics. Never return provider bodies or local filesystem paths."""

import re


def public_error(exc: Exception) -> str:
    value = str(exc)
    if "ModelNotOpen" in value:
        return "This model is not activated. Enable it in the Ark console's model activation page."
    if "401" in value or "403" in value:
        return "Model authentication failed. Check the API key and model permissions (401/403)."
    if "429" in value:
        return "The model is rate limited. Please try again later (429)."
    if "timeout" in value.lower() or "timed out" in value.lower():
        return "The operation timed out. Your saved work is available; try again later."
    if isinstance(exc, (ValueError, FileNotFoundError)) and not re.search(
        r"[/\\]|key|token", value, re.I
    ):
        return value[:300]
    return "The operation failed. Check provider configuration or retry. Saved work is unchanged."
