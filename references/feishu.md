# 飞书读取、写入与恢复

本机创建时实测 lark-cli 1.0.79。下列命令是这个版本的参数范式，变量用真实回包填入；每次运行仍须查看本机版本、相应子命令 --help 以及 CLI 内置的 lark-doc 指南（含 fetch、XML、create、update 或 media-insert 对应章节）。缺命令时查实际等价能力，不猜参数，不自动升级。全程显式 --as user。用户只要草稿时不写远端。

## 先取 JD

只使用本次指定的 JD 入口和归档位置。先按 Wiki token 解析 space_id、node_token、obj_type 和 obj_token。文档读写用 docx 对象 ID，建子文档用父 Wiki 节点 token。若 JD 来自普通外部链接或本地文件，直接读取该来源，跳过 Base 流程；若归档格式或平台不是飞书，改按 formats.md 处理。

若 JD 索引是飞书多维表格，探测实际表与字段；按公司、岗位、版本消歧，再取 JD 单元格。它可能含全文、富文本或仅一个招聘链接；仅有链接时必须读取链接所指的该职位原文。以下变量来自当前调用及回包：
```bash
lark-cli wiki spaces get_node --as user --token "$wiki_token"
lark-cli base +url-resolve --as user --url "$jd_entry_url"
lark-cli base +table-list --as user --base-token "$base_token"
lark-cli base +field-list --as user --base-token "$base_token" --table-id "$table_id"
lark-cli base +record-list --as user --base-token "$base_token" --table-id "$table_id" --format json --field-id "$company_field" --field-id "$role_field"
lark-cli base +record-get --as user --base-token "$base_token" --table-id "$table_id" --record-id "$record_id" --field-id "$jd_field" --format json
```
Base list 结果需按 fields 与 record_id_list 解读对应 data 行。优先用 --filter-json 缩小范围；按实际表/字段/记录分页接口取完候选页。只读相关字段。若入口改为普通文档，先读正文中的索引、内嵌表和链接；若以 Wiki 子节点组织，用节点回包中的 space_id 与父 node_token 遍历实际子树，处理分页和快捷方式循环。

仅对齐空白、全半角、大小写以找候选，同时核实完整公司和岗位名。简称、同集团子公司、同名不同级别/地区/业务线、不同发布日期等不自动合并。有多个候选时列出区分项、来源链接，请用户选；无匹配、正文为空、外链失效、登录/验证码、链接职位与记录不符时，说明具体卡点，请求相应权限、正确链接或用户提供的原始全文和可归属的来源链接。不要绕开登录；等待时仅整理已拿到的原话。版头完整保留原 JD 的文字、数字、条件与类别内顺序；展示时按正文展示规范将岗位职责、任职资格、加分项各归并为一格，移除额外序号列，不逐条拆行；剔除页面导航与广告。JD 在格内即全文时使用记录定位链接（若只有可验证的表链接，将 table_id/record_id 只写入本地来源清单，正文使用可读链接名）；外链 JD 保留真实职位 URL，附表来源。PDF/图片需核实全文；缺页先询问。

## 确定写入位置

```bash
lark-cli wiki +node-list --as user --space-id "$space_id" --parent-node-token "$archive_node" --page-all --page-limit 0
lark-cli docs +fetch --as user --doc "$doc_id" --scope outline
lark-cli docs +fetch --as user --doc "$doc_id" --detail full
```
只在用户指定父节点直接子级查公司文档。读标题和版头公司，解析实际节点类型；模板、快捷方式、同名公司和疑似旧名先核实。模板文档只读。唯一且可核实则复用，多候选请用户选，查不全或无权列目录不能按“公司不存在”新建。确认无匹配才创建“公司全称｜面试复盘”。同一公司不同岗位仍用该文档；新版 JD 在版头最后一个 JD 段与首轮之间局部插入，不替换旧 JD，各轮标明使用哪个版本。无法安全定位时停止写入。

## 增量提交

1. 为公司／岗位、面试轮次类型、已知日期建立业务身份；按原始文件字节或原文本 UTF-8 计算 SHA-256。多文件将有序的各文件摘要组成清单再哈希；不要用模型输出或随机数做指纹。正文只显示轮次标题、岗位、日期、原文件名；来源指纹与block对应关系留在本地清单，用清单及已有内容查重。禁止将SHA、token、table_id、record_id、block_id、机器段号或本地绝对路径作为正文文字。旧文档可能没有指纹，需比对日期、轮次、岗位和问答。相同轮次相同来源且完整则复用，不再追加；同轮不同源、不同轮相同源、冲突或无法判断则询问是补充、更正还是另一场。已填黄色块永远保留。用户明确要更正时只改授权的具体块。
2. 准备完整本地 XML 及按块的写入清单。模板有版头、轮次、题目、可选诊断和本轮报告。构造元素时用 XML 序列化器转义正文和链接，不做字符串插入；保留换行、尖括号、&、反引号。长逐字稿按同一发言或其连续片段分开，逐段编号定位。用 XML 解析检查根、必需块，问答文本与已校验的标点整理稿须逐字相等；另按 [标点整理](punctuation.md) 校验整理稿与原始稿只有阅读标点差异；不得把模板 wrapper、占位文本或假 source 标签发给飞书。
3. 同公司所有写入串行；同机器跨运行用同一父节点＋规范公司键的操作系统文件锁，覆盖第二次查询、创建、追加至最终回读；可运行 `python3 scripts/company_write.py "$archive_node" "$canonical_company" python3 本轮写入计划.py`；计划程序须在锁内重新查重并完成全部提交和回读，不要每条 CLI 单独加锁。没有锁／有其他写者时先串行协调。新建接口无跨设备唯一约束；多客户端同时可能新建时，先确定单一写入者，出现双节点停下核对，不自动删。写前重读目标父级和文档最新修订号，核实锚点没有漂移。已有文档用明确 revision-id 和新增块；禁止对公司文档整篇 overwrite。用户明确要求清理或改版时，仅局部修改其授权范围，保留原视频、问答原话、其他轮次和已填写黄色块；没有清理授权时不删除既有内容。
4. 下列命令先用 --dry-run 核对 parent/doc/命令/内容。读写结果按退出状态、ok、warnings/degrade_details、回读实际块判断；dry-run 不证明内容已经写入。新建可把版头和第一轮一次写入；已有文档仅追加新的轮次；增补新版 JD 时用当前版头最后一个顶层块。
```bash
lark-cli docs +create --as user --parent-token "$archive_node" --title "$company_title" --doc-format xml --content @company.xml
lark-cli docs +update --as user --doc "$doc_id" --revision-id "$revision" --command append --doc-format xml --content @round.xml
lark-cli docs +update --as user --doc "$doc_id" --revision-id "$revision" --command block_insert_after --block-id "$header_anchor" --doc-format xml --content @jd-version.xml
```
5. 需要分批时按版头、完整题目、本轮报告等边界写入，记录来源、计划块、锚点、最后已核实的区间及当前 revision。中途失败重新回读，比对实际顶层块、原文、题号、本轮报告边界及本地提交清单，确定唯一缺失后缀才补；不能确认边界则停止，不回放整批。提交结束状态只记本地，不为校验向正文插入带哈希的结束标识；视频是否到位必须另验。遇修订冲突刷新并重新判断，最多再做一次安全的增量写入。曾被人修改的内容和空块中的笔记均保留。
6. 附视频时按 [原视频归档](video.md) 核验文件与位置。最后回读 --detail full，核对父子关系、公司唯一、版头 JD 全文及链接、轮次标题、题号/原话及标点整理稿、引用块、淡黄色 callout 内空 p、本轮报告、全部回答代码块的原生自动换行状态，以及正文无附录、技术ID或结束指纹；各视频必须为本轮的真实附件。重复执行时以现有 block id、内容和完整性比对，用户已填写的输入块视为有效，绝不为了验空而清空。

## 失败如何处理

- 读请求限流或 5xx：遵循 Retry-After，否则退避，最多两次额外尝试。写请求超时、断网或响应不明，先读远端；已写复用，明确未写且原因可恢复时最多重试一次。部分写入按上述清单续写；仍不明则留草稿和已确认的文档位置，向用户说明哪一段待核实。
- 区分身份登录失效、缺 scope、无源表读取权、无目标节点建子文档权、无当前文档编辑／媒体上传权。说明资源、操作和实际 code/message，按实际缺项询问授权或替代路径；不自行切换 bot、扩权、换父节点或公开分享。CLI 要求明确高风险确认时不绕过。
- 若命令或样式版本不兼容，查本机内置指南和帮助。Rich XML 实测回读时 light-yellow 可能序列化为 RGB 而非原色名。若空 p 被吞、代码块或 quote 降级、原文丢失，列出具体缺陷，仅在确认定位的本次新增块上局部修复一次；仍失败则保留草稿，不以普通 Markdown、占位字或截图冒充可编辑黄色框。

## 展示与样式

创建前必须读 [正文展示规范](presentation.md)。XML `<pre>` 本身不保证自动换行，写后用 `scripts/wrap_code_blocks.py` 设置并验证实际 `code.style.wrap=true`；不靠伪造XML属性或插入硬换行通过检查。公司文档含多轮时，清理某轮附录必须以该轮边界为限，不能从首个附录删到整篇末尾。原始完整转写、逐题五维证据、SHA与来源/块映射均保留本地。
