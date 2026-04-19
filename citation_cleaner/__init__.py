"""citation-cleaner: find hallucinated citations in research PDFs."""

from citation_cleaner.parse import Citation
from citation_cleaner.verify import VerificationResult, Verdict

__version__ = "0.1.0"
__all__ = ["Citation", "VerificationResult", "Verdict", "__version__"]
