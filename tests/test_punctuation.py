import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('punctuation', Path(__file__).resolve().parents[1] / 'scripts/check_punctuation.py')
punctuation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(punctuation)


class PunctuationChecks(unittest.TestCase):
    def test_readable_punctuation_preserves_repetitions(self):
        punctuation.check_pair('嗯嗯我我负责这个项目你呢', '嗯，嗯，我，我负责这个项目。你呢？')

    def test_existing_reading_punctuation_can_be_normalized(self):
        punctuation.check_pair('对, 是吗?', '对， 是吗？')

    def test_number_and_technical_tokens_are_preserved(self):
        punctuation.check_pair('版本v3.7预算1.85调用ASR/TTS', '版本v3.7，预算1.85，调用ASR/TTS。')

    def test_changed_words_and_case_are_rejected(self):
        for before, after in [('我同意', '我不同意。'), ('嗯嗯好', '嗯，好。'), ('AI', 'ai。')]:
            with self.subTest(before=before), self.assertRaises(ValueError):
                punctuation.check_pair(before, after)

    def test_decimal_and_version_punctuation_cannot_be_changed(self):
        for before, after in [('1.85', '185。'), ('v3.7', 'v37。'), ('API', 'A.PI。')]:
            with self.subTest(before=before), self.assertRaises(ValueError):
                punctuation.check_pair(before, after)

    def test_markers_and_inline_code_are_protected(self):
        for before, after in [('[听不清 00:02:11–00:02:14]', '[听不清 00:02:11–00:02:14？]'),
                              ('`a,b`', '`a，b`')]:
            with self.subTest(before=before), self.assertRaises(ValueError):
                punctuation.check_pair(before, after)

    def test_url_query_is_protected(self):
        with self.assertRaises(ValueError):
            punctuation.check_pair('https://example.org/?q=a', 'https://example.org/q=a')

    def test_empty_answers_stay_empty(self):
        punctuation.check_pair('', '')
        with self.assertRaises(ValueError):
            punctuation.check_pair('', '。')

    def test_whitespace_and_newlines_are_preserved(self):
        punctuation.check_pair('好\n 下一题', '好。\n 下一题。')
        with self.assertRaises(ValueError):
            punctuation.check_pair('好\n 下一题', '好。下一题。')

    def test_summary_and_duplicate_identifiers(self):
        pair = {'id': 'Q01', 'before': '你呢', 'after': '你呢？'}
        self.assertEqual(punctuation.check_pairs([pair]), {'checked': 1, 'changed': 1, 'punctuation_only': True})
        for items in [[], [pair, pair]]:
            with self.subTest(items=items), self.assertRaises(ValueError):
                punctuation.check_pairs(items)


if __name__ == '__main__':
    unittest.main()
