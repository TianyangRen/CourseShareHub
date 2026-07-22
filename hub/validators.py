"""
File-upload validators.  OWNER: Zhihan (File Upload — §5.5).

Attached to Resource.file. They power the Testing (/2) edge cases: rejecting
oversized files and disallowed extensions with a clear form error instead of
crashing.
"""
import os

from django.core.exceptions import ValidationError

MAX_UPLOAD_MB = 10
ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.png', '.jpg', '.jpeg', '.gif']


def validate_file_size(value):
    """Reject files larger than MAX_UPLOAD_MB megabytes."""
    limit = MAX_UPLOAD_MB * 1024 * 1024
    if value.size > limit:
        raise ValidationError(f'File too large. Maximum size is {MAX_UPLOAD_MB} MB.')


def validate_file_extension(value):
    """Reject files whose extension is not in the allow-list."""
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError('Unsupported file type. Allowed: ' + ', '.join(ALLOWED_EXTENSIONS))
