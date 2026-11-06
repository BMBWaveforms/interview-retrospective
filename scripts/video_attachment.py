"""Insert an original video once, at one top-level Lark Docs text anchor."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def cli(args, cwd=None):
    process = subprocess.run(["lark-cli", *args, "--as", "user"], cwd=cwd,
                             capture_output=True, text=True)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or "飞书命令失败，先回读文档再重试。")
    response = json.loads(process.stdout)
    if response.get("ok") is not True or response.get("identity") != "user":
        raise RuntimeError("飞书返回状态或身份不符。")
    return response["data"]


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def at_anchor(doc, anchor):
    data = cli(["docs", "+fetch", "--doc", doc, "--detail", "full"])["document"]
    blocks = list(ET.fromstring("<root>" + data["content"] + "</root>"))
    matches = [i for i, block in enumerate(blocks)
               if anchor in "".join(block.itertext())]
    if len(matches) != 1:
        raise ValueError("定位文字未唯一命中，本次未插入。")
    index = matches[0]
    block = blocks[index]
    if (block.tag not in ("p", "h1", "h2", "h3") or
            "".join(block.itertext()) != anchor):
        raise ValueError("定位文字须为一个独立且完整的顶层段落或标题。")
    return blocks[index + 1] if index + 1 < len(blocks) else None


def verify(block, source, expected_hash):
    if block is None or block.tag != "figure" or block.get("view-type") != "Preview":
        raise ValueError("视频位置或预览模式待核对，请勿重复上传。")
    media = block.find("source")
    if (media is None or not media.get("token") or
            media.get("size") != str(source.stat().st_size)):
        raise ValueError("附件信息不完整或大小不同。")
    with tempfile.TemporaryDirectory() as folder:
        cli(["docs", "+media-download", "--token", media.attrib["token"],
             "--output", "original.bin"], cwd=folder)
        if digest(Path(folder) / "original.bin") != expected_hash:
            raise ValueError("该位置附件与原视频内容不符。")
    return {"block_id": block.get("id"), "name": media.get("name"), "sha256": expected_hash}


def run(args):
    source = args.original.resolve(strict=True)
    expected_hash = digest(source)
    block = at_anchor(args.document, args.anchor)
    if block is not None and block.tag in ("figure", "source", "img"):
        return {"status": "已复用", **verify(block, source, expected_hash)}
    # A failed request can have server-side effects. Never replay it in this tool.
    cli(["docs", "+media-insert", "--doc", args.document, "--file", "./" + source.name,
         "--type", "file", "--file-view", "preview", "--selection-with-ellipsis",
         args.anchor], cwd=source.parent)
    checked = verify(at_anchor(args.document, args.anchor), source, expected_hash)
    return {"status": "已插入", **checked}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", help="docx document_id")
    parser.add_argument("anchor", help="Unique top-level text in the round")
    parser.add_argument("original", type=Path)
    try:
        print(json.dumps(run(parser.parse_args()), ensure_ascii=False))
    except (OSError, KeyError, RuntimeError, ValueError, ET.ParseError) as exc:
        sys.exit(f"原视频归档待核对：{exc}")
