"""The instructions for one capture, shared by the worker (parent) and capture_cli (child).

Keep this file free of heavy imports: no Django, no Playwright.
"""
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class CaptureSpec:
    owner: str
    repo: str
    sha: str
    page_path: str
    out_path: str
    width: int
    height: int
    full_page: bool

    def __post_init__(self):
        # Runs automatically right after the dataclass sets the fields above.
        for name in ("owner", "repo", "sha", "page_path", "out_path"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty string, got {value!r}")

        for name in ("width", "height"):
            value = getattr(self, name)
            # type() rather than isinstance(): in Python, True and False count as ints!
            if type(value) is not int or not 100 <= value <= 5000:
                raise ValueError(f"{name} must be a whole number from 100 to 5000, got {value!r}")

        if type(self.full_page) is not bool:
            raise ValueError(f"full_page must be true or false, got {self.full_page!r}")

    @classmethod
    def from_json(cls, text):
        # A missing or unknown key raises TypeError here, which is what we want.
        return cls(**json.loads(text))