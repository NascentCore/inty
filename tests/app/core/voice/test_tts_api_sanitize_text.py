"""Tests for app.core.voice.tts_api: sanitize_text_for_gemini_tts (split by parens into stage_directions and dialogue)."""

from app.core.voice.tts_api import sanitize_text_for_gemini_tts


class TestSanitizeTextForGeminiTts:
    def test_keeps_first_paren_block_removes_later_ones(self):
        text = """(After your successful presentation, your secretary entered your room to congratulate you.)
"So, you're tired aren't you?"
(She closes the door behind her and locks it)
"sir, what can I do for you..?"
"""
        stage_directions, dialogue = sanitize_text_for_gemini_tts(text)
        assert stage_directions == [
            "After your successful presentation, your secretary entered your room to congratulate you.",
            "She closes the door behind her and locks it",
        ]
        assert dialogue == [
            "",
            "\n\"So, you're tired aren't you?\"\n",
            '\n"sir, what can I do for you..?"\n',
        ]

    def test_only_one_paren_block(self):
        text = '(Stage direction here.) "Dialogue only."'
        stage_directions, dialogue = sanitize_text_for_gemini_tts(text)
        assert stage_directions == ["Stage direction here."]
        assert dialogue == ["", ' "Dialogue only."']

    def test_no_parens(self):
        text = '"Just dialogue."'
        stage_directions, dialogue = sanitize_text_for_gemini_tts(text)
        assert stage_directions == []
        assert dialogue == ['"Just dialogue."']

    def test_multiple_later_blocks_removed(self):
        text = '(First.) "A" (Second.) "B" (Third.) "C"'
        stage_directions, dialogue = sanitize_text_for_gemini_tts(text)
        assert stage_directions == ["First.", "Second.", "Third."]
        assert dialogue == ["", ' "A" ', ' "B" ', ' "C"']

    def test_empty_string(self):
        stage_directions, dialogue = sanitize_text_for_gemini_tts("")
        assert stage_directions == []
        assert dialogue == [""]

    def test_unclosed_first_paren(self):
        text = "(unclosed"
        stage_directions, dialogue = sanitize_text_for_gemini_tts(text)
        assert stage_directions == []
        assert dialogue == ["", "unclosed"]

    def test_unclosed_first_paren_with_more_text(self):
        text = '(unclosed "dialogue"'
        stage_directions, dialogue = sanitize_text_for_gemini_tts(text)
        assert stage_directions == []
        assert dialogue == ["", 'unclosed "dialogue"']
