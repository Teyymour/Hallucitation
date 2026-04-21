"""hallucitation: find hallucinated citations in research PDFs."""

from hallucitation.parse import Citation
from hallucitation.verify import VerificationResult, Verdict

__version__ = "0.1.0"
__all__ = ["Citation", "VerificationResult", "Verdict", "__version__"]
