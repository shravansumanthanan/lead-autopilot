import pytest
from services.content_validator import ContentValidator

def test_detect_repetitive_sentences():
    validator = ContentValidator()
    
    # Needs 3 identical sentences to trigger
    text = "This is a great product. We love it. This is a great product. It works well. This is a great product."
    assert validator.detect_repetitive_content(text) is True
    
    # 2 sentences should not trigger
    text_ok = "This is a great product. We love it. This is a great product. It works well."
    assert validator.detect_repetitive_content(text_ok) is False

def test_detect_repetitive_paragraphs():
    validator = ContentValidator()
    
    # Needs 2 identical paragraphs to trigger
    text = "We offer tremendous value through our services.\n\nWe offer tremendous value through our services."
    assert validator.detect_repetitive_content(text) is True

def test_no_repetition():
    validator = ContentValidator()
    text = "Our platform is scalable. It helps businesses grow fast. \n\nWe leverage cloud capabilities."
    assert validator.detect_repetitive_content(text) is False

def test_empty_string():
    validator = ContentValidator()
    assert validator.detect_repetitive_content("") is False
