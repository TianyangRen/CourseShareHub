"""
File-upload validators.  OWNER: Zhihan (File Upload — §5.5).

Attached to Resource.file. They power the Testing (/2) edge cases: rejecting
oversized files and disallowed extensions with a clear form error instead of
crashing.
"""
import os

from django.core.exceptions import ValidationError

# Module-level constants (not hardcoded inline) so the limits can be reused —
# e.g. shown in a form's help_text or asserted directly from a test — without
# repeating the numbers/list in more than one place.
MAX_UPLOAD_MB = 10
ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.png', '.jpg', '.jpeg', '.gif']


# Plain module-level functions, not methods or lambdas: Django writes a
# validators=[...] reference into each migration, and a function importable by
# dotted path (hub.validators.validate_file_size) is what makes that migration
# reproducible on another machine — a lambda or a bound method can't be
# serialized the same way.
def validate_file_size(value):
    """Reject files larger than MAX_UPLOAD_MB megabytes."""
    limit = MAX_UPLOAD_MB * 1024 * 1024
    if value.size > limit:
        raise ValidationError(f'File too large. Maximum size is {MAX_UPLOAD_MB} MB.')


def validate_file_extension(value):
    """Reject files whose extension is not in the allow-list."""
    # Compare the lower-cased extension only — checking content-type instead
    # would be stricter, but the assignment's scope only asks for a clear form
    # error on a disallowed extension, not deep file-content sniffing.
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError('Unsupported file type. Allowed: ' + ', '.join(ALLOWED_EXTENSIONS))
