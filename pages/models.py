from django.db import models

class SubmissionThrottle(models.Model):
    """Short-lived, keyed hashes used to coordinate limits across workers."""

    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
