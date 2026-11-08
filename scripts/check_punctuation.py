"""Validate punctuation-only transcript edits from JSON pairs on stdin.

This checks source fidelity, not the linguistic quality of sentence boundaries.
"""
import json
import re
import sys

READING_PUNCTUATION = frozenset('，。！？；：、…“”‘’?,.!;:')
PROTECTED = (
    r'\d+(?:[.:/-]\d+)*',
    r'\[[^\]\n]*\]|【[^】\n]*】',
    r'`[^`\n]*`',
    r'https?://[^\s<>“”‘’，。！？；：、]+',
    r'[A-Za-z0-9]+(?:[._/+:#-][A-Za-z0-9]+)+',
)


def check_pair(before, after):
    if not isinstance(before, str) or not isinstance(after, str):
        raise ValueError('before 和 after 必须为字符串')
    if not before.strip() and before != after:
        raise ValueError('未作答的空白不能补入标点或占位文字')
    strip = lambda text: ''.join(c for c in text if c not in READING_PUNCTUATION)
    if strip(before) != strip(after):
        raise ValueError('字词、空白、大小写或结构字符发生变化')
    for pattern in PROTECTED:
        if re.findall(pattern, before) != re.findall(pattern, after):
            raise ValueError('数字、技术结构、代码、URL或不确定标记发生变化')


def check_pairs(items):
    if not isinstance(items, list) or not items:
        raise ValueError('输入必须为非空的问答对照数组')
    seen = set()
    changed = 0
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('每个对照项必须为对象')
        key = item.get('id')
        if not isinstance(key, str) or not key.strip() or key in seen:
            raise ValueError('每个对照项必须有唯一非空 id')
        seen.add(key)
        try:
            check_pair(item.get('before'), item.get('after'))
        except ValueError as exc:
            raise ValueError(f'{key}: {exc}') from exc
        changed += item['before'] != item['after']
    return {'checked': len(items), 'changed': changed, 'punctuation_only': True}


if __name__ == '__main__':
    try:
        print(json.dumps(check_pairs(json.load(sys.stdin)), ensure_ascii=False))
    except (ValueError, TypeError) as exc:
        sys.exit(f'标点校验失败：{exc}')
