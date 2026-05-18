import re
from collections import Counter

class ContentValidator:
    """
    Validates text content to ensure it meets quality standards,
    specifically focusing on detecting AI hallucinations like repetitive loops.
    """

    def detect_repetitive_content(self, text: str) -> bool:
        """
        Detects if the text contains high levels of repetition, 
        indicating a possible AI hallucination or loop.
        
        Rules:
        - Same sentence repeated 3 or more times.
        - Same paragraph repeated 2 or more times.
        """
        if not text:
            return False

        # 1. Check paragraph-level repetition
        # Split by 2 or more newlines
        paragraphs = [p.strip().lower() for p in re.split(r'\n{2,}', text) if len(p.strip()) > 20]
        para_counts = Counter(paragraphs)
        if any(count >= 2 for count in para_counts.values()):
            return True

        # 2. Check sentence-level repetition
        # Split by punctuation
        sentences = [s.strip().lower() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 10]
        sent_counts = Counter(sentences)
        if any(count >= 3 for count in sent_counts.values()):
            return True

        return False
