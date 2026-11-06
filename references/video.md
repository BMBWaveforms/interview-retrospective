# 每轮插入原视频

视频输入同时承担转写来源和归档原件两种用途。将用户提供的原始文件逐个插在对应轮次开头，在问答前展示；保持文件名、字节内容、顺序和原音轨。转写用的音频、转码副本、截图、播放器封面或外链不能替代原视频。纯音频和纯文本无需视频块。只给流媒体地址或缺少原件时先向使用者索要原视频或可获授权下载的原文件地址，已经能做的部分先保存。

以下步骤用于飞书。其他目标按 [格式适配](formats.md) 交付原视频及核验字节。

1. 写正文时为每个视频生成单独的顶层定位段，如“原视频 1｜文件名｜本轮材料标识｜文件 SHA-256”；必须在该文档唯一。保留同轮多视频的原始顺序。先回读确认轮次、锚点、附件现状，无覆盖冲突才写。若附件已在本轮，核验其 file_token、大小和内容指纹后复用，即使文件后来改名也不重复插。同名不同指纹不得替换。锚点变动／重复或同位置已出现未识别附件时先停下核对。
2. 本机 lark-cli 1.0.79 实测支持下列操作。先看本机帮助和 CLI 内置 references/lark-doc-media-insert.md。传 docx 的 document_id，不传 wiki URL。工作目录选原视频所在目录，--file 传其下相对路径；分别作为 argv 传入，保留原文件名。选择唯一锚点，显式指定 preview，避免默认追加到整篇末尾。
```bash
lark-cli docs +media-insert --as user --doc "$doc_id" --file "$relative_original" --type file --file-view preview --selection-with-ellipsis "$unique_anchor"
lark-cli docs +fetch --as user --doc "$doc_id" --detail full
```
在保持公司写入锁、检查本轮是否已有移位附件之后，优先运行随包脚本：
`python3 scripts/video_attachment.py "$doc_id" "$unique_anchor" "$original_file"`。脚本会检查唯一锚点，在紧邻位置已有附件时回下载比对原件；内容冲突会停止。用于其他版本前先核对 CLI 能力。

3. 返回 ok 仍要核实：所选轮次内定位段之后有 figure（view-type=Preview），source 文件名、字节数、token 正确，视频顺序与清单一致。用本次返回的 block_id/file_token 回读交叉校验。新写或来源存疑时按实际权限用 `lark-cli docs +media-download --as user --token "$file_token" --output "$new_relative_file"` 下载到临时目录，对比 SHA-256，再清理临时副本。遇预览渲染能力不足，仍可归档原件；准确说明是“原件附件、预览待确认”，不要承诺所有客户端或编码均可内联播放。
4. 上传失败、超限、权限不足或返回不明，先回读轮次和媒体块。已绑定且一致就复用；孤立块、未知回包或不同内容不盲目重传、不删除用户文件。仅在确认本次未落地且可修复时重试一次。保留已完成的问答和附录，明确报告“原视频待补”；需要另一个原文件／位置时询问用户。没有用户同意不得改用链接代替原视频并报已完成。
