"""Tests for app.core.voice.tts_api: santize_text_for_gemini_tts (keep first (), remove rest)."""

import pytest

from app.core.voice.tts_api import santize_text_for_gemini_tts


class TestSantizeTextForGeminiTts:
    def test_keeps_first_paren_block_removes_later_ones(self):
        text = """(After your successful presentation, your secretary entered your room to congratulate you.)
"So, you're tired aren't you?"
(She closes the door behind her and locks it)
"sir, what can I do for you..?"
"""
        # 第二个 (…) 整段去掉后，其后的 \n 保留，故两段对话之间多一空行
        want = """(After your successful presentation, your secretary entered your room to congratulate you.)
"So, you're tired aren't you?"

"sir, what can I do for you..?"
"""
        assert santize_text_for_gemini_tts(text) == want

    def test_only_one_paren_block_unchanged(self):
        text = '(Stage direction here.) "Dialogue only."'
        assert santize_text_for_gemini_tts(text) == text

    def test_no_parens_unchanged(self):
        text = '"Just dialogue."'
        assert santize_text_for_gemini_tts(text) == text

    def test_multiple_later_blocks_removed(self):
        text = '(First.) "A" (Second.) "B" (Third.) "C"'
        # 去掉 (Second.) 与 (Third.) 后，原 ) 后的空格保留，故 "A" "B" "C" 间各多一空格
        want = '(First.) "A"  "B"  "C"'
        assert santize_text_for_gemini_tts(text) == want

    def test_empty_string(self):
        assert santize_text_for_gemini_tts('') == ''
