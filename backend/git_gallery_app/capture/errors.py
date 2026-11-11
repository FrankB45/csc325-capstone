class CaptureError(Exception):
    """A capture failed for a reason we can explain to the user.

    The message is saved as the capture's failure reason and shown in the UI,
    so write it for a designer or manager, not a developer.
    """
