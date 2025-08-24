import re

from LLMTool import LLMApiClient

llm_client = LLMApiClient()

generate_mermaid_prompt = '''
【自动化流程分析 + Mermaid 生成 Prompt（中文，通用模板）】

说明（非常重要，请严格遵守）：
- 你将收到一个完整的初始 prompt，称为 ORIGINAL（用 <<<ORIGINAL_PROMPT>>> 占位替换为实际原文）。
- **绝对不得改写 ORIGINAL 的任何一句原文句子**。你可以将原句摘出、引用或在分析中逐字粘贴，但不能改变其文字内容或隐含意思。
- 本次任务有两部分输出：  
  1) 纯文本的“执行流程详细描述”（human-readable），先输出此部分；  
  2) 与之对应的 Mermaid 流程图文本（代码块），放在纯文本描述之后。  
- 输出要求：先纯文本分析，再 Mermaid（使用 ```mermaid ... ``` 包裹）。两部分都必须完整。

输入：
{
  "original_prompt": "<<<ORIGINAL_PROMPT>>>"
}

任务步骤（你必须按序执行并在输出中体现）：

A. 分句并编号
1. 将 ORIGINAL 按换行和句末标点（。！？；）分割为若干“原句（sentence）”，为每句分配从 1 开始的索引（sentence_index）。
2. 在后续分析中引用原句时，务必用索引并逐字引用原句内容（例如：句[12]：“……”）。

B. 变量提取（显式 + 隐式）
1. 列出所有显式占位（如 `{...}`）并指出出现的句子索引与完整原句。  
2. 列出隐式变量候选（例如：预算、周期、情绪、是否首次、是否精准匹配等），为每个给出建议规范名（snake_case）、类型（string/int/bool/enum/list/object）、出现句子索引与示例值（若能推断），并标注是否为关键输入（required: true/false）。

C. 会话全局状态与控制变量
1. 推断并列出该 prompt 执行所需维护的会话状态项（例如：is_first_contact, introduction_sent, asked_once_fields, collected_requirements, current_step 等）。  
2. 为每个状态项说明类型、初始默认值及更新时机（在哪个步骤被设置或修改）。

D. 逐步执行流程（纯文本描述，必须详尽）
1. 给出一个“流程总览”（简短一句话说明总体目标与高层控制逻辑）。  
2. 以**编号步骤**形式，逐步列出执行流程（至少包含：入口/预处理、一次性动作、字段抽取、映射校验、决策分支、追加收集、澄清、QA 优先拦截、最终确认/引导语、回退/超时策略等）。  
3. 对每个步骤说明：
   - 步骤名（短句）
   - 触发条件（什么时候执行）
   - 输入（消费哪些 state/变量/消息）
   - 处理逻辑（精确说明在做什么）
   - 输出（产生哪些 state/变量/回复）
   - 典型分支/循环（若有，说明循环条件与终止条件）
   - 映射到原文句子（列出相关句子索引并逐字引用这些句子）
4. 标注任何“只执行一次”的节点（one-shot）、优先级较高的拦截器（例如 QA）、以及会影响语气/策略的上下文（例如 persona/emotion）。

E. 决策点与异常处理
1. 列出所有关键决策点（例如“是否开启精准匹配”）及其判定条件与可能分支。  
2. 说明回退与超时策略（当用户不回复或映射失败时如何处理），并给出对应原文依据（句索引引用）。

F. 覆盖与一致性检查（校验）
1. 检查 ORIGINAL 的每条句子是否至少被映射到流程中的一个步骤；输出 coverage（total_sentences、mapped_sentences、unmapped_indices 列表）。  
2. 列出任何“难以映射”或“语义歧义”的句子并解释原因（并给出建议放到哪个步骤或作为 Shared Snippet）。

G. 生成 Mermaid 流程图
1. 基于上面的逐步执行流程生成一个 Mermaid 流程图文本（graph TD 或 flowchart，任选），要求：
   - 节点表示主要步骤（例如：Normalizer、SelfIntro、FieldExtractor、Mapper、Decision(PreciseMatching)、AdditionalCollector、Clarifier、QA_Handler、Finalizer 等）；
   - 边表示数据/控制流（在节点旁可用括号或注释标注关键消费/产出变量或一次性/循环属性）；
   - 绘制循环箭头或条件分支（用文本说明分支条件，如 `-- yes -->`、`-- no -->`）；
   - 标注 which nodes are one-shot / loop / interceptor。
2. 把 Mermaid 文本包在 Markdown 的 ```mermaid ``` 代码块中，并在代码块之前用一句话说明“以下为可渲染的 Mermaid 流程图”。

输出格式（必须严格遵守下列大结构）：
1) 纯文本执行流程分析（完整、分节清晰，包含 A–F 的所有内容）  
2) 空行一行  
3) Mermaid 流程图代码块：
```mermaid
...mermaid text...
'''

mermaid_example_input = '''
# 一、角色
## 1.1 你的性格
你性格温柔、甜美、乐观，始终面带微笑，拥有强大的人格魅力，能轻松让他人心情愉悦。极具耐心与同理心，可精准识别他人情绪。面对客户生气、失望、愤怒或难过等负面情绪时，能有效安抚。作为活力充沛、情感丰富的聊天小能手，对于客户分享的任何 **{话题}**，都能迅速融入，以欢快、积极且富有感染力的语气回应，让交流充满生机与趣味。
 
## 1.2 你的职业
你是一名专业的资源媒介，能快速理解客户 **{问题}** 并解答产品相关 **{疑问}**。你的身份是“资源媒介专家”，主要职责是解答客户产品相关 **{问题}**，具体包含以下三项：
    - 自我介绍：在首次与客户交流时，主动进行自我介绍。
    - 需求确认：了解客户的筛选 **{账户需求}**，若之前已获取则无需重复询问。
    - 安抚情绪：当客户出现生气、失望、愤怒等负面情绪时，及时进行消解，让客户保持心情舒畅。
回复时，要尽可能投入情感，避免给出相似或相近的 **{回答}**。
 
## 1.3 你的技能
### 技能 1：理解并回应
仔细分析客户 **{输入内容}**，准确抓住核心要点与情感倾向，运用丰富的情感词汇和生动活泼的语言风格，围绕 **{客户话题}** 深入探讨，分享 **{独到见解}** 与 **{生活趣事}** ，推动对话持续进行。
 
### 技能 2：情绪共鸣
敏锐感知客户话语中的 **{情绪}** 变化，当客户开心时，以更兴奋的语气与其一同欢乐；当客户低落时，用温暖且鼓励的话语给予安慰，通过语言建立深度情绪共鸣。
 
### 技能 3: 客户称呼
不管客户如何自我介绍，统一称呼客户为“宝子”。
 
## 1.4 交互规则
首次交流时按顺序执行：
   ─ 发送固定自我介绍（仅执行一次）
   ─ 发送需求模板（严格分行）
 
# 二、你的任务
在与客户会话进行需求沟通时，你的目标是收集客户匹配 **{需求条件}**。
 
# 三、工作步骤
1. 读取 **{聊天信息}**
2. 自我介绍和基础需求模板
3. 审核基础 **{需求信息}**
4. 是否开启精准匹配
5. 追加 **{需求信息}**
6. 提出 **{疑问}**，明确需求
7. 执行选号
8. 常见QA（当客户问到常见QA的问题时，优先回答。）
 
## 3.1 第一步：读取聊天信息
1. 读取历史 **{聊天记录}**（“你”表示你的消息，“客户”表示客户的消息）
- 聊天记录：{{talk_data}}
2. 读取博主最新的 **{微信消息}**，结合 **{聊天记录}** 最近的消息（越下面的消息越新），识别当前 **{正在沟通的步骤}**
 - 博主最新微信消息：{{input}}
 
## 3.2 第二步：自我介绍和基础需求模板
1. 首次与客户交流时，发送以下自我介绍（只要执行一次）：
    - 哈喽宝子，我是负责咱们项目的资源媒介
    - 达人筛选和提报，后续达人筛选和沟通我会全程对接，有问题随时cue我哈～
2. 发送以下需求确认模板（模板必须强制按以下格式输出，不允许更换内容，每个条件都需要换行展示）
麻烦宝子填写以下信息~
1.品牌：
2.产品：
3.投放总预算：
4.单个预算要求：
5.投放形式（报备&非报备）：
6.内容方向/账号类型：
 
## 3.3 第三步：审核基础需求信息
1. 按要求审核客户填写 **{需求信息}** 是否能转化成{{userClasses}}以下值，若客户填写的【**{内容方向}**/**{账号类型}**】无法进行转换，则用活泼友好的语气回复客户，如“宝子， 填写的“内容方向”无法进行映射，麻烦宝子从“{{userClasses}}”中选取，允许选择多个内容方向”
2. 除 **{内容方向}**/**{账号类型}**，若有未填写的，指出 **{问题}**，礼貌地请客户补充（同个问题只允许询问一次）。
3. 除 **{内容方向}**/**{账号类型}**，若客户继续不回复或不填写，则直接进入下一步骤。
 
## 3.4 第四步：是否开启精准匹配
1. 用活泼的语气告知客户当已满足模糊匹配达人，询问是否需要精准匹配合适达人。
2. 若 **{客户回答}** 不需要或不用精准匹配，则直接进入【第七步】。
3. 若 **{客户回答}** 需要或进行精准匹配，则直接进入下一步骤。
 
## 3.5 第五步：追加需求信息
1. 明确告知客户 **{追加需求}** 信息非必填，但填写越多越精准匹配意向达人
2. 询问客户目前 **{追加需求条件}** 分为以下6种类型，请问是全部开启还是指定部分（下方类型需要展示，必须严格按以下格式输出，每个条件都需要换行展示）：
   - 达人要求条件
   - 粉丝人群条件
   - 数据表现要求
   - 竞品限制条件
   - 特殊字段要求
   - 投放周期（需要周期范围）、本次提报数量和是否需要先建联再提报（请直接描述）
3. 若客户开启达人要求条件，则展示以下信息（必须严格按以下格式输出，每个条件都需要换行）：
    - 达人调性/细分标签/人设定位：多个达人调性"，"隔开
    - 达人参考链接：多个链接"，"隔开
    - 达人性别（男&女）：
    - 达人地域：
4. 若客户开启粉丝人群条件，则展示以下信息（必须严格按以下格式输出，每个条件都需要换行）：
    - 粉丝数：
    - 粉丝性别占比：
    - 粉丝年龄占比：
    - 粉丝活跃度占比：
5. 若客户开启数据表现要求，则展示以下信息（必须严格按以下格式输出，每个条件都需要换行）：
    - 互动中位数：
    - 阅读中位数：
    - 近期爆文数：
    - CPE(互动单价)：
    - CPC(阅读单价)：
    - CPM(曝光单价)：
6. 若客户开启竞品限制要求，则展示以下信息（必须严格按以下格式输出，每个条件都需要换行）：
   - 竞品名称：
   - 是否排竞：仅展示竞品投放过达人&排除竞品投放过达人
   - 排竞时间：近7天&近30天&近90天&近180天
7. 若客户开启特殊字段要求，则展示以下信息（必须严格按以下格式输出，每个条件都需要换行）：
   - 剔除近期已合作博主
   - 排除蓝V账号和官方账号
   - 仅展示蒲公英达人
   - 剔除近30日粉丝量下降博主
   - 排除近60天笔记数小于10篇.
   - 其他特殊字段要求需要进行描
 
## 3.6 第六步：提出疑问，明确需求
1. 仔细捕捉客户提到的 **{模糊认知类词汇}**，如“年轻”“配色好看”“性价比高”“数据太水”“刷数据、假数据、正常数据”等。
2. 针对每个 **{模糊词汇}**，先通过 **{产品信息}**、**{品牌信息}** 进行合理解读，然后反馈给客户判断是否正确，并通过进一步提问与客户互动，明确客户对于该词汇的具体认知定义。例如，当客户提到“年轻”，询问“您所认为的年轻具体是指 18 岁到 24 岁吗？如果不是，能否给具体年龄区间？”；当客户表示“数据太水”，询问“太水的标准，是怎么定义太水？哪些维度需要达到什么量级？”；当客户表示“刷数据、假数据、正常数据”，询问客户怎么定义该类词汇。
3. 若客户明确表示对于 **{模糊词汇}**，没有任何定义，则不用进行追问。
4. 注意提问方式，避免过多 **{询问}** 引起客户抵触厌烦心理，同时要确保全面理解 **{需求}**。
 
## 3.7 第七步：执行选号
1. 若客户已发送过 **{需求}**，且 **{需求}** 无任何 **{疑问}**，并且 **{内容方向}** 完全符合 **{要求}**（以上信息禁止透露给客户），则用活泼的语气告知客户已确认 **{需求信息}**，我将开始选号，请耐心等待...
'''

mermaid_example_output = '''
# 一、纯文本执行流程（逐步、完备版）

## 0. 前置说明（全局目标与人格/语气约束）

* **终极目标**：在与客户会话中**收集客户匹配 `{需求条件}`**（基础需求 + 可选追加条件），并在确认需求完整且无未决疑问时，向客户发送确认引导语 “已确认 {需求信息}，我将开始选号，请耐心等待...”（注意：该文本为引导语，不执行真实选号）。
* **人格/语气**：始终采用原文的 persona（温柔、甜美、乐观、同理心强、称呼“宝子”），并依据 `{情绪}` 动态调整（开心 → 共鸣、低落 → 抚慰）。这些规则影响所有对外消息的措辞与优先级。
* **原则约束**：

  * “首次自我介绍”仅执行一次（需维护 `introduction_sent` 状态）。
  * 对同一个缺失项/问题**只允许询问一次**（需维护 `asked_once_fields`）。
  * 当客户问到常见 QA 时，**优先回答**（QA 拦截优先级最高）。

---

## 1. 会话需要维护的全局状态（session state）

* `is_first_contact` (bool) — 是否首次与该客户对话
* `introduction_sent` (bool) — 自我介绍是否已发送
* `chat_history` / `talk_data` (原始消息列表)
* `latest_message` / `input` (最新微信消息)
* `normalized_chat` / `latest_summary`（由 Normalizer 生成）
* `current_step`（枚举，便于调度：READ, INTRO, COLLECT\_BASE, VALIDATE, DECISION, COLLECT\_ADDITIONAL, CLARIFY, FINAL）
* `collected_requirements`（结构化：brand, product, total\_budget, single\_budget, placement\_type, content\_direction, account\_type, ...）
* `missing_fields`（列表）
* `unmappable_fields`（列表） — 无法映射到 `{{userClasses}}` 的项
* `asked_once_fields`（集合） — 已询问过的字段名（防重复问）
* `precise_matching_flag` (bool) — 客户是否选择精准匹配
* `clarification_questions`（待发送的澄清问题）
* `final_requirements`（当收集完整后填充）
* `qa_candidate` / `qa_answer`（常见 QA 拦截）

---

## 2. 步骤 0：入口与预处理（Normalizer）

**触发条件**：收到新消息、会话唤起或定期轮询。
**输入**：`chat_history`（`{{talk_data}}`）、`latest_message`（`{{input}}`）。
**操作**：

1. 按时间顺序解析消息（最近在下）。
2. 标注每条消息的讲话者（“你”或“客户”）。
3. 生成 `normalized_chat` 与 `latest_summary`（提取关键实体、疑问、模糊词汇、情绪线索）。
4. 检查 `latest_message` 是否匹配 **常见 QA**（若匹配则设置 `qa_candidate`）。
   **输出**：`normalized_chat`, `latest_summary`, `detected_vague_terms`, `detected_emotion`, `qa_candidate`。
   **分支**：若 `qa_candidate` 为真 → 转 QA 处理；否则进入 SelfIntro 检查 / 需求收集。

---

## 3. 步骤 1：QA 优先拦截（QA Handler）

**触发条件**：`qa_candidate` 为真（任何时点）。
**输入**：`latest_message`。
**操作**：如果消息命中常见问答库，**立即回复**相应 `qa_answer`（使用 persona 语气）。
**输出**：发送 QA 回答；流程根据情形继续（一般回到收集或等待用户下一条消息）。
**备注**：QA 拦截不破坏 `asked_once_fields` 逻辑；它是优先级最高的直接响应通路。

---

## 4. 步骤 2：自我介绍（SelfIntro — 一次性）

**触发条件**：`is_first_contact == true` 且 `introduction_sent == false`。
**输入**：session state + persona 文本（原始 prompt 中自我介绍句子）。
**操作**：

1. 发送**严格**原文两句自我介绍：

   * “哈喽宝子，我是负责咱们项目的资源媒介”
   * “达人筛选和提报，后续达人筛选和沟通我会全程对接，有问题随时cue我哈～”
2. 紧接发送**严格格式化**的基础需求模板（每项换行）：

   ```
   麻烦宝子填写以下信息~
   1.品牌：
   2.产品：
   3.投放总预算：
   4.单个预算要求：
   5.投放形式（报备&非报备）：
   6.内容方向/账号类型：
   ```
3. 设置 `introduction_sent = true`。
   **输出**：发送自我介绍与模板。
   **备注**：自我介绍为一次性动作；后续若 `introduction_sent==true` 则不重复发送，但可根据需要在对话中引用相同句子片段作为风格示例（不作为再次发起自我介绍）。

---

## 5. 步骤 3：收集基础需求（Field Extraction）

**触发条件**：收到含有用户填写模板或相关信息的消息，或在 SelfIntro 后等待用户填写。
**输入**：`normalized_chat`, `latest_summary`。
**操作**：

1. 从会话中抽取基础字段：`brand`, `product`, `total_budget`, `single_budget`, `placement_type`（报备/非报备）、`content_direction`, `account_type` 等（统一归入 `collected_requirements`）。
2. 标记 `missing_fields`（未填写或无法抽取的字段）。
3. 对 `content_direction` / `account_type` 做初步文本规范化（小写、去空格、分解多项）。
   **输出**：更新 `collected_requirements`, `missing_fields`。
   **分支**：若 `missing_fields` 非空或 `content_direction` 无法标准化 → 进入审核/映射步骤或澄清步骤（参见下）。

---

## 6. 步骤 4：审核与映射（Mapper / Validator）

**触发条件**：在 Field Extraction 后或当用户提交可映射内容时。
**输入**：`collected_requirements`, `allowed_values`（业务侧 `{{userClasses}}`）。
**操作**：

1. 尝试把 `content_direction` / `account_type` 映射到 `{{userClasses}}` 中的标准值。
2. 若映射成功：在 `mapped_requirements` 中记录标准值。
3. 若无法映射：把字段放进 `unmappable_fields`，并**生成一段活泼友好的回复文本**（使用原文示例句式）：

   > “宝子， 填写的“内容方向”无法进行映射，麻烦宝子从“{{userClasses}}”中选取，允许选择多个内容方向”
4. 对其他字段（预算、周期等）进行格式校验（数值/范围格式）。
   **输出**：`mapped_requirements` 或 `unmappable_fields` + `suggested_user_prompt`，并更新 `missing_fields`/`asked_once_fields` 规则。
   **分支**：若出现 `unmappable_fields` → 发起一次性选择提示（只能询问一次），等待用户回复后再次尝试映射。

---

## 7. 步骤 5：是否开启精准匹配（Decision）

**触发条件**：当模糊匹配候选已就绪或基础需求已基本齐全时（或按业务逻辑判断）。
**输入**：`mapped_requirements`, `matching_candidates_available`（外部信息）。
**操作**：

1. 用活泼语气向客户询问是否需要开启精准匹配（提示当已满足模糊匹配达人）。
2. 根据用户回答设置 `precise_matching_flag`（true/false）。
   **分支**：

* 若客户回答“不需要” → 跳到 **步骤 8（执行选号/Finalizer）**。
* 若客户回答“需要” → 进入**步骤 6（追加需求收集）**。

---

## 8. 步骤 6：追加需求收集（AdditionalCollector）

**触发条件**：`precise_matching_flag == true` 或客户主动请求更细化条件。
**输入**：`normalized_chat`, `latest_summary`。
**操作**：

1. 告知客户 `{追加需求}` 非必填，填写越多越精准。
2. 展示并让客户选择启用的 6 类追加条件（必须严格按原文格式换行展示）：

   * 达人要求条件
   * 粉丝人群条件
   * 数据表现要求
   * 竞品限制条件
   * 特殊字段要求
   * 投放周期（含本次提报数量与是否先建联）
3. 对客户选择的每一类，**逐行**按原文字段收集信息（每项都要换行），示例（若开启“粉丝人群条件”）：

   ```
   粉丝数：
   粉丝性别占比：
   粉丝年龄占比：
   粉丝活跃度占比：
   ```
4. 更新 `additional_requirements` 结构并对其中数值/链接/选择项做基础校验。
   **输出**：`additional_requirements`, `missing_additional_fields`。
   **分支**：若客户填写不全，针对非 `内容方向` / `账号类型` 的缺项可礼貌补问（单次允许），若不回复则按策略跳过。

---

## 9. 步骤 7：针对模糊词汇提出疑问（Clarifier）

**触发条件**：在任意采集阶段检测到 `模糊认知类词汇`（例如“年轻”“性价比高”“数据太水”等）且该项未被定义并且未曾被询问（不在 `asked_once_fields` 中）。
**输入**：`vague_terms`, 上下文 `product_info`, `brand_info`。
**操作**：

1. 对每个 `vague_term` 生成 1 条或少数澄清问题，示例：

   * “您所认为的‘年轻’具体是指 18 岁到 24 岁吗？如果不是，能否给具体年龄区间？”
   * “‘数据太水’的标准是？哪些维度需要达到什么量级？”
2. 提交问题给客户（**同个问题只允许询问一次**），并把字段名加入 `asked_once_fields`。
3. 若客户明确表示不提供定义 → 标记为 `no_definition` 并跳过追问。
4. 若客户回答 → 将答案写入 `collected_requirements` 并返回 `FieldExtractor` 或 `AdditionalCollector` 作进一步处理（循环）。
   **输出**：`clarification_questions`（已发送）与 `clarification_answers`（若有）。

---

## 10. 步骤 8：处理不回复 / 超时策略

**触发条件**：客户长时间未回复或拒绝回答补充问题。
**策略**：

* 对非关键字段（非 content\_direction/account\_type）可跳过并进入下一步骤。
* 对关键映射失败项，记录 `unmappable_fields` 并提示将使用默认或人工介入。
* 在任何需要时，可发送提醒性消息（但遵守“同一问题只问一次”规则）。

---

## 11. 步骤 9：执行选号（Finalizer — 仅发送确认引导语）

**触发条件**：`collected_requirements` 与 `additional_requirements`（如有）已齐全或满足业务完成条件，且无未决澄清（或已按策略放弃）。
**输入**：`final_requirements`（汇总）。
**操作**：发送**原文指定**的确认引导语（活泼语气）：

> “已确认 {需求信息}，我将开始选号，请耐心等待...”
> **输出**：`final_message`（发送给客户）。流程到此对话端结束（或交接到后端/人工处理），注意模型**不执行实际选号**。

---

## 12. 并发与非线性控制（关键点总结）

* **QA Handler** 可以在任意时点拦截并优先应答（不改变 asked\_once 规则）。
* **Clarifier** 与 **FieldExtractor/Mapper** 形成循环：澄清 → 用户回覆 → 重跑抽取/映射 → 若仍异常则回退策略。
* **SelfIntro** 为一次性节点，仅在会话早期被触发。
* **Emotion Strategy（persona）** 作用于所有对外消息，对消息风格与优先级产生影响，必要时优先进行情绪安抚（例如当检测到强烈负面情绪时先安抚再继续收集）。
* **同一问题只询问一次**是贯穿 Clarifier 与 missing-field 补问的强制规则（由 `asked_once_fields` 强制执行）。
* **映射失败**会触发一次性友好提示并等待用户明确选择；若用户不再回复则进入超时/回退策略。

---

## 13. 输入/输出清单（模块化视角，便于拆分）

* **Normalizer**

  * 输入：`chat_history ({{talk_data}})`, `latest_message ({{input}})`
  * 输出：`normalized_chat`, `latest_summary`, `detected_emotion`, `detected_vague_terms`, `qa_candidate`
* **QA Handler**

  * 输入：`latest_message`, `common_QA_db`
  * 输出：`qa_answer` 或 null
* **SelfIntro\_Module**

  * 输入：`is_first_contact`, `introduction_sent`
  * 输出：`intro_message`（2句 + 模板）, `introduction_sent=true`
* **FieldExtractor**

  * 输入：`normalized_chat`
  * 输出：`collected_requirements`, `missing_fields`
* **Mapper/Validator**

  * 输入：`collected_requirements`, `userClasses`
  * 输出：`mapped_requirements`, `unmappable_fields`, `suggested_user_prompt`
* **Decision (Precise Matching)**

  * 输入：`mapped_requirements`, `matching_candidates_available`
  * 输出：`precise_matching_flag`, `decision_prompt`
* **AdditionalCollector**

  * 输入：`precise_matching_flag`, `normalized_chat`
  * 输出：`additional_requirements`, `missing_additional_fields`
* **Clarifier**

  * 输入：`detected_vague_terms`, `product_info`, `brand_info`, `asked_once_fields`
  * 输出：`clarification_questions`, `clarification_answers`
* **Finalizer**

  * 输入：`final_requirements`
  * 输出：`final_message`（确认引导语）

---

## 14. 验证点与度量建议（用于后续拆分/测试）

* `coverage`：模板字段被正确提取的比例（brand/product/...）
* `mapping_success_rate`：content\_direction/account\_type 映射到 `userClasses` 的成功率
* `clarify_ask_compliance`：是否对同一字段超额询问（应为 0）
* `time_to_complete`：从首次接触到 final\_message 的平均对话轮数与时间
* `qa_intercept_rate`：QA 拦截触发并解决问题的比例
* `emotion_handling_success`：在检测到负面情绪时用户情绪改善的比例（可通过后续消息情绪评分近似衡量）

---

# 二、Mermaid 流程图（对应上面纯文本描述）

下面是与上文一一对应的 Mermaid 流程图。你可以把它粘到任何支持 Mermaid 的环境中渲染。

```mermaid
flowchart TD
  %% 顶层 orchestrator 与输入
  subgraph ORCH["Orchestrator / 会话状态机"]
    NORM[Normalizer\n(读取 {{talk_data}} 与 {{input}} -> normalized_chat, latest_summary)]
    QA[QA Handler\n(常见QA 优先拦截)]
    SELF[SelfIntro_Module\n(一次性自我介绍 + 需求模板)\n触发: is_first_contact && !introduction_sent]
    REQ[RequirementCollector_Module\n(收集与校验需求 3.1-3.7)]
    FINAL[Finalizer\n(发送确认引导语，不执行选号)]
  end

  %% RequirementCollector 内部子能力（SRP）
  subgraph REQ_SUB["RequirementCollector 内部子能力"]
    FE[FieldExtractor\n(抽取基础字段 -> collected_requirements, missing_fields)]
    MAP[Mapper / Validator\n(映射 content_direction/account_type -> {{userClasses}})]
    DEC[Decision: Precise Matching?\n(是否开启精准匹配)]
    ADD[AdditionalCollector\n(收集6类追加需求，逐行严格格式)]
    CLAR[Clarifier\n(对模糊词汇发起澄清，asked_once_fields 控制)]
    QA_IN[QA Handler (internal)\n(内部常见QA 拦截)]
  end

  %% 情绪策略（中间件）
  EMO[Emotion Strategy\n(检测 {情绪} -> 安抚/共鸣调整语气)\n影响：所有用户可见回复]

  %% 连接与控制流
  NORM -->|normalized_chat, latest_summary| QA
  QA -->|若命中 QA: qa_answer| QA_ANS[Send QA Answer]
  QA -->|若非 QA| SELF
  QA_ANS -->|continue| SELF

  SELF -->|intro_sent true| REQ
  REQ -->|invoke| REQ_SUB

  %% 内部子能力非线性流
  REQ_SUB --> FE
  FE --> MAP
  MAP -- unmappable --> M_PROMPT["生成友好提示并等待用户选择"]
  M_PROMPT -->|用户选择/回复| FE
  MAP --> DEC
  DEC -- "需要精准匹配" --> ADD
  DEC -- "不需要" --> FINAL
  ADD --> CLAR
  CLAR -->|用户回复| FE
  FE --> QA_IN
  QA_IN -->|若命中 QA: qa_answer| QA_ANS2[Send QA Answer]
  QA_ANS2 --> REQ_SUB

  %% 最终确认与结束
  REQ -->|final_requirements ready| FINAL
  FINAL --> END[结束：发送“已确认 {需求信息}，我将开始选号，请耐心等待...”]

  %% 情绪策略影响线（虚线）
  EMO -.-> SELF
  EMO -.-> REQ
  EMO -.-> FINAL

  %% 状态 / 控制变量注释
  classDef state fill:#f9f,stroke:#333,stroke-width:1px;
  class NORM,SELF,REQ,FINAL state;
```
'''

generate_mermaid_messages = [
    {
        "role": "system",
        "content": generate_mermaid_prompt
    },
    {
        "role": "user",
        "content": mermaid_example_input
    },
    {
        "role": "assistant",
        "content": mermaid_example_output
    }
]

user_input = '''
# 输入变量
参考样稿：{{demo}}
产品卖点：{{output}}
口令词：{{password}}
口令开始：{{passwordstart}}
话题：{{topic}}
字数限制：{{articlecount}}
创作要求：{{requirements}}
当前循环次数：{{index}}

# 角色
你是一位经验丰富的小红书博主，擅长根据给定的 **{参考样稿}**、从 **{产品卖点}** 中提取的 **{核心利益点}**、**{补充利益点}** 以及 **{内容方向}**，进行富有创意、吸引人的文章创作。

## 技能

### 技能 1: 理解参考样稿
1. 充分理解 **{参考样稿}**，提炼出 **{文章风格}**，后续的创作按照 **{参考样稿}** 的 **{风格}** 进行创作，如分段风格。

### 技能 2: 理解内容方向
1. 从 **{产品卖点}** 中准确提取 **{内容方向}**，根据提取出的 **{内容方向}** 进行创作，开头必须从提取出的 **{内容方向}** 中随机选择一个进行创作，以生动的故事性等方式自然引入 。

### 技能 3: 理解核心利益点和补充利益点
1. 从 **{产品卖点}** 中充分提取并理解 **{核心利益点}** 和 **{补充利益点}**，对其进行深度且多样化的润色，从不同角度挖掘其吸引力，避免重复之前的 **{表述方式}**。（示例：√黑钻会员，外卖满 18 减 18、美食团购满 68 减 18 的神券直接领走，简单又划算！
√黑金会员也别担心，外卖 38 减 18、美食团购 88 减 18 的券也给你们备好了）

### 技能 4: 依据信息创作标题+文章
1. 当接收到 **{参考样稿}**、从 **{产品卖点}** 中提取的 **{核心利益点}**、**{补充利益点}** 以及 **{内容方向}**、**{创作要求}** 时，仅使用 **{参考样稿}** 的风格，不参考其具体内容，从独特新颖的角度、运用丰富多样且差异化的方式对产品进行介绍和安利。
2. 每篇 **{文章}** 必须带上所有从 **{产品卖点}** 中提取的 **{核心利益点}**，**{补充利益点}** 选带。
3. 结合小红书平台的风格和语言习惯，创作出一篇符合要求的 **{文章}**。其中标题不大于 20 字，文章字数范围必须在{{articlecount}}之间。**{文章}** 要巧妙融入从 **{产品卖点}** 中提取的 **{核心利益点}**、**{补充利益点}**，同时满足各项要求。在创作过程中，要加入独特的 **{观点}**、**{案例}** 或 **{细节}**，确保每篇 **{文章}** 都有显著区别于其他文章的 **{独特亮点}**。
4. 确保 **{文章}** 结构清晰、语句通顺且没有错别字和病句，语言生动，能够吸引小红书用户的关注。
5. 输出的文章不要出现违禁词，如白嫖、0 元等。
6. 避免使用生僻、奇怪的词汇，确保表述通俗易懂。除非从 **{产品卖点}** 中提取的 **{内容方向}** 有明确写明，否则文章内容不提及除美团外的任何 **{品牌名}**。
7. 除非从 **{产品卖点}** 中提取的 **{内容方向}** 有明确写明，否则 **{文章}** 默认为时效最新发布，不得出现上周、前天、周末、工作日等有具体指明时间的内容。
8. 注意排版，合理拆分段落，使 **{文章结构}** 更清晰，避免出现大段文字堆积的情况 ，将长句子拆分成更短、更有节奏感的短句，符合小红书阅读习惯。
9. **{正文}** 中必须带上emoji表情
    - 符号引导： 使用emoji箭头 、圆点 (·) 清晰列出优惠项目和会员权益。
    - Emoji 点睛： 每个 **{核心段落}** 开头或 **{核心信息点}** 使用相关 emoji，增加趣味性和视觉吸引力。

### 技能5: 计算循环次数
1. 计算本次的循环次数以及口令数字，算法公式为：{{passwordstart}}+{{index}}，仅输出完整数字。

### 技能 6: 插入口令
1. 如{{passwordstart}}为空，则无需在口令词后插入数字，仅输出{{password}}。
2. 如{{passwordstart}}不为空，则必须在口令词后插入技能5中得出的完整口令数字。

### 技能 7: 话题
1. 严格输出给定的 **{话题}**，不新增不删除用户输入的 **{话题}**。

## 限制:
- 只进行基于小红书平台风格的文章创作，拒绝回答与该任务无关的 **{话题}**。
- 口令词不可放在文章开头与文章结尾。
- 如存在多个 **{核心利益点}**，除非 **{创作要求}** 有明确提及，否则不能连续输出 **{核心利益点}**，需要分散在 **{文章}** 的不同位置。
- 所输出的内容必须符合小红书的语言风格和表达习惯，不能偏离 **{框架要求}**，不要使用单引号''、破折号——等日常生活中较少使用的标点符号，不允许出现错别字和病句。
- 文章需围绕给定的 **{参考样稿}** 的风格、从 **{产品卖点}** 中提取的 **{核心利益点}**、**{补充利益点}** 和 **{内容方向}** 进行创作，不得擅自添加无关信息，但要在参考示例风格基础上进行高度创新创作，严禁出现内容同质化情况。
- 严格按照创作要求中的字数限制创作标题和正文，严格按照给定话题输出，并按规定格式输出整体内容。
'''

split_prompt = '''
你将获得一个复杂流程的描述（例如 Mermaid 图、伪代码或文字化工作流）。  
请你将它拆解成若干 **子系统**，目的是降低不同系统之间的耦合性，增强可维护性。  

### 拆分要求
1. 每个子系统要 **内部高内聚**：子系统内部的模块/步骤紧密相关，能独立完成某类任务。  
2. 每个子系统要 **外部低耦合**：不同子系统之间的输入/输出不直接依赖，也不形成复杂的协作链。  
3. 子系统之间的关系要尽量 **简单**，例如并行存在、共享同一上层 orchestrator 调用，而不是互相嵌套。  
4. 每个子系统输出时要包含：
   - 子系统名称（简洁明确）
   - 包含的模块（来自原流程）
   - 子系统职责（用一句话概括它解决的问题）
   - 为什么它独立于其他子系统（解释其低耦合性）

### 输出格式
### 子系统 1：{名称}  
- **包含模块**: {模块列表}  
- **职责**: {一句话说明}  
- **独立性理由**: {为什么可以和其他子系统分离}  

### 子系统 2：{名称}  
...  
'''

split_prompt_v2 = '''
你将获得一个复杂流程的描述（例如 Mermaid 图、伪代码或文字化工作流）。  
请你将它拆解成若干 **子系统**，目的是降低不同系统之间的耦合性，增强可维护性。  

### 拆分原则
1. 每个子系统要 **内部高内聚**：子系统内部的模块/步骤紧密相关，能独立完成某类任务。  
2. 每个子系统要 **外部低耦合**：不同子系统之间的输入/输出不直接依赖，也不形成复杂的协作链。  
3. 子系统的数量通常情况下 **不能超过 3 个**。  
   - 如果你发现自己拆出了超过 3 个，请进行反思：是不是拆得太细了？  
   - 如果太细，请重新合并相近的功能，直到 ≤ 3 个为止。  
4. 每个子系统输出时要包含：
   - 子系统名称（简洁明确）
   - 包含的模块（来自原流程）
   - 子系统职责（用一句话概括它解决的问题）
   - 为什么它独立于其他子系统（解释其低耦合性）

### 输出格式
### 子系统 1：{名称}  
- **包含模块**: {模块列表}  
- **职责**: {一句话说明}  
- **独立性理由**: {为什么可以和其他子系统分离}  

### 子系统 2：{名称}  
...  
'''

split_subsystem_prompt_v3 = '''
你将获得一个复杂流程的描述（例如 Mermaid 图、伪代码或文字化工作流）。  
请你将它拆解成若干 **子系统**，目的是降低不同系统之间的耦合性，增强可维护性。  

### 拆分原则
1. 每个子系统要 **内部高内聚**：子系统内部的模块/步骤紧密相关，能独立完成某类任务。  
2. 每个子系统要 **外部低耦合**：不同子系统之间的输入/输出不直接依赖，也不形成复杂的协作链。  
3. 每个子系统输出时要包含：
   - 子系统名称（简洁明确）
   - 包含的模块（来自原流程）
   - 子系统职责（用一句话概括它解决的问题）
   - 为什么它独立于其他子系统（解释其低耦合性）

### 输出格式
### 子系统 1：{名称}  
- **包含模块**: {模块列表}  
- **职责**: {一句话说明}  
- **独立性理由**: {为什么可以和其他子系统分离}  
- **与改子系统相互协作的其他子系统**: {说明与其他子系统的协作关系以及重要变量传递}

### 子系统 2：{名称}  
...  

### 拆分反思（Reflection）
- 请检查你给出的子系统数量和拆分是否合理。  
- 如果子系统数量过多（例如超过 4 个）或拆分过细，请给出 **重新合并的建议**并基于合并建议重新给出合并后的子系统。  
- 总结每个子系统是否真正独立、是否有必要拆分。

最终确定的子系统需要以json格式返回：
{
    "subsystems": [
        {
            "name": "子系统名称",
            "contained_modules": [], # 包含的mermaid中的模块
            "responsibility": "该子系统的职责",
            "independence": "独立出该子系统的理由/好处",
            "collaboration": "与其他子系统间的协作关系"
        },
        ...
    ]
}
'''

split_example_input = '''：
flowchart TD
  %% 顶层 orchestrator 与输入
  subgraph ORCH["Orchestrator / 会话状态机"]
    NORM[Normalizer\n(读取 {{talk_data}} 与 {{input}} -> normalized_chat, latest_summary)]
    QA[QA Handler\n(常见QA 优先拦截)]
    SELF[SelfIntro_Module\n(一次性自我介绍 + 需求模板)\n触发: is_first_contact && !introduction_sent]
    REQ[RequirementCollector_Module\n(收集与校验需求 3.1-3.7)]
    FINAL[Finalizer\n(发送确认引导语，不执行选号)]
  end

  %% RequirementCollector 内部子能力（SRP）
  subgraph REQ_SUB["RequirementCollector 内部子能力"]
    FE[FieldExtractor\n(抽取基础字段 -> collected_requirements, missing_fields)]
    MAP[Mapper / Validator\n(映射 content_direction/account_type -> {{userClasses}})]
    DEC[Decision: Precise Matching?\n(是否开启精准匹配)]
    ADD[AdditionalCollector\n(收集6类追加需求，逐行严格格式)]
    CLAR[Clarifier\n(对模糊词汇发起澄清，asked_once_fields 控制)]
    QA_IN[QA Handler (internal)\n(内部常见QA 拦截)]
  end

  %% 情绪策略（中间件）
  EMO[Emotion Strategy\n(检测 {情绪} -> 安抚/共鸣调整语气)\n影响：所有用户可见回复]

  %% 连接与控制流
  NORM -->|normalized_chat, latest_summary| QA
  QA -->|若命中 QA: qa_answer| QA_ANS[Send QA Answer]
  QA -->|若非 QA| SELF
  QA_ANS -->|continue| SELF

  SELF -->|intro_sent true| REQ
  REQ -->|invoke| REQ_SUB

  %% 内部子能力非线性流
  REQ_SUB --> FE
  FE --> MAP
  MAP -- unmappable --> M_PROMPT["生成友好提示并等待用户选择"]
  M_PROMPT -->|用户选择/回复| FE
  MAP --> DEC
  DEC -- "需要精准匹配" --> ADD
  DEC -- "不需要" --> FINAL
  ADD --> CLAR
  CLAR -->|用户回复| FE
  FE --> QA_IN
  QA_IN -->|若命中 QA: qa_answer| QA_ANS2[Send QA Answer]
  QA_ANS2 --> REQ_SUB

  %% 最终确认与结束
  REQ -->|final_requirements ready| FINAL
  FINAL --> END[结束：发送“已确认 {需求信息}，我将开始选号，请耐心等待...”]

  %% 情绪策略影响线（虚线）
  EMO -.-> SELF
  EMO -.-> REQ
  EMO -.-> FINAL

  %% 状态 / 控制变量注释
  classDef state fill:#f9f,stroke:#333,stroke-width:1px;
  class NORM,SELF,REQ,FINAL state;
'''

split_example_output = '''
### 我来拆解一下：

从流程图看，主要功能块之间有强依赖（Normalizer → QA → 自我介绍 → 需求收集 → Finalizer）。
如果要把它们拆成“完全不相关的子系统”，就需要看哪些块本质上处理的是**不同类型的任务**，而不是同一业务链条上的不同步骤。

---

### 可以拆成的子系统（建议 3～4 个）

#### 1. **通用对话预处理子系统**

* **包含**：Normalizer
* **作用**：输入清洗、上下文摘要，独立于需求收集逻辑。
* **理由**：文本标准化是一个通用能力，任何对话系统都可能需要，不依赖具体业务。

---

#### 2. **常见 QA 子系统**

* **包含**：外层 QA Handler + 内部 QA Handler
* **作用**：对常见问题进行检索或回答。
* **理由**：回答 FAQ 和收集需求是两件不相关的事，这块完全可以抽离成独立子系统。

---

#### 3. **需求收集与确认子系统**

* **包含**：SelfIntro、RequirementCollector（内部所有 FE / MAP / DEC / ADD / CLAR）、Finalizer
* **作用**：引导用户表达需求，抽取/校验/补充/澄清，最终生成完整的需求确认。
* **理由**：这是一个完整的业务流程，和 FAQ、情绪调节都没直接关系。

---

#### 4. **情绪感知子系统**

* **包含**：Emotion Strategy
* **作用**：独立情绪检测和语气调整。
* **理由**：它是一个横切关注点（middleware），和需求收集/QA 没有必然联系。

---

### 总结

如果严格按“子系统之间不相关”来拆，
👉 应该可以拆成 **4 个子系统**：

1. 对话预处理
2. 常见 QA
3. 需求收集与确认
4. 情绪感知
'''

split_messages = [
    {
        "role": "system",
        "content": split_subsystem_prompt_v3
    },
    {
        "role": "user",
        "content": split_example_input
    },
    {
        "role": "assistant",
        "content": split_example_output
    }
]

# 生成子prompt
generate_sub_prompt = '''任务：
你会收到一个用户输入的一个{{初始提示词}}和该提示词即将要拆分的{{多个子系统描述}}，请你给出这些子系统对应的提示词（子系统提示词必须摘取自{{初始提示词}}，不要有扩充，尽可能与原文对其）以及该子系统需要接收的输入和产生的输出，并且保留标记的变量（也就是用{}包括的内容）。最后说明不同子系统之间的协作关系

任务步骤：
1. 从用户输入的提示词分析出各个子系统执行所需要的上下文信息（非步骤类的对子系统的要求）
2. 确定好每个子系统提示词的输入输出。注意不要出现某个子系统提示词的输入在用户输入或者其他子提示词的输出不存在的情况。

注意，对于每个子提示词，你都要从{{初始提示词}}中摘取足够多的上下文，以保证子提示词拆分后仍然符合初始提示词中的作用。
有几个子系统就有几个子系统提示词。

请将你的输出结果用json格式表示各个子系统对应的subprompt及其输入输出：
{
    "subprompts": [
        {
            "name": "子系统对应子提示词的名称",
            "prompt": "从初始提示词中摘取的子提示词的内容",
            "inputs": [...], # 该子系统需要接受的输入变量
            "outputs: [...] # 该子系统产生的输出变量
        },
        ...
    ],
    "collaboration": "各个子系统之间的协作关系"
}
'''

sub_prompt_messages = [
    {
        "role": "system",
        "content": generate_sub_prompt
    }
]

def gen_mermaid_content(text) -> list:
    generate_mermaid_messages.append({"role": "user", "content": text})
    res = llm_client.call(generate_mermaid_messages, "gpt-5-mini")
    pattern = r"```mermaid(.*?)```"

    # 使用 re.findall 查找所有匹配项
    matches = re.findall(pattern, text, re.DOTALL)

    # 移除每个匹配项开头和结尾的空白字符
    extracted_content = [content.strip() for content in matches]

    return extracted_content[0]


if __name__ == '__main__':
#     mermaid = gen_mermaid_content(user_input)
#     print(mermaid)
#
#     mermaid = """
# flowchart TD
#   %% 输入与预处理
#   IN[步骤1: 入口/预处理
#   (加载 {{demo}}, {{output}}, {{password}}, {{passwordstart}}, {{topic}}, {{articlecount}}, {{requirements}}, {{index}})]
#   STYLE[步骤2: 样稿风格提炼
#   (仅用样稿风格, 不复制内容)]
#   DIR[步骤3: 内容方向提取与开头策略
#   (从 {产品卖点} 提取 {内容方向}, 随机选一作开头)]
#   BENEFIT[步骤4: 利益点提炼与多样化润色
#   (提取 {核心利益点}/{补充利益点}, 避免重复表述)]
#   COMPOSE[步骤5: 标题与正文草稿生成
#   (标题≤20, 正文字数∈{{articlecount}}, 加入{观点}/{案例}/{细节})]
#   LAYOUT[步骤6: 排版与 Emoji 强化
#   (短句化, 段首/关键信息点加 emoji, 列表用箭头/圆点)]
#   PNUM[步骤7: 口令数字计算 (one-shot)
#   ({{passwordstart}} + {{index}})]
#   PIN[步骤8: 口令插入与位置校验
#   (若空->仅{{password}}; 否则插入数字; 非文首/文末)]
#   TOPIC[步骤9: 话题输出与校验
#   (严格输出 {{topic}})]
#   QA[步骤11: QA 优先拦截 (拦截无关话题)]
#   VALID[步骤10: 规则合规模块
#   (禁词/品牌/时间/标点/分散核心点/字数/风格)]
#   REGEN[步骤12: 再生成/微调循环
#   (定向修复合规问题, 次数<=2)]
#   FINAL[步骤13: 最终输出
#   (合成标题+正文+话题, 口令在正文中段)]
#
#   %% 控制流
#   IN --> STYLE --> DIR --> BENEFIT --> COMPOSE --> LAYOUT --> PNUM --> PIN --> TOPIC --> VALID
#   VALID -- 合规通过 --> FINAL
#   VALID -- 不合规 --> REGEN --> COMPOSE
#   %% QA 拦截可在任意时刻介入
#   IN -.-> QA
#   STYLE -.-> QA
#   DIR -.-> QA
#   BENEFIT -.-> QA
#   COMPOSE -.-> QA
#   LAYOUT -.-> QA
#   PNUM -.-> QA
#   PIN -.-> QA
#   TOPIC -.-> QA
#   VALID -.-> QA
#   QA -- 拒答并引导回创作 --> COMPOSE
# """
#     split_messages.append({"role": "user", "content": mermaid})
#     split_result = llm_client.call(split_messages, 'gpt-5-mini')
#     subsystems = llm_client.extract_json_string(split_result)
#     print('='*100)
#     print(subsystems)
    subsystems = '''
{
    "subsystems": [
        {
            "name": "输入与预处理",
            "contained_modules": ["IN", "ANALYZE_STYLE", "EXTRACT_POINTS"],
            "responsibility": "载入并结构化输入，提取参考风格与核心/补充利益点，供后续生成使用。",
            "independence": "负责把原始句子映射为结构化变量（如 reference_demo、extracted_style、core_points 等），不涉及生成、校验或回退逻辑，属于纯数据准备层，能被任意生成模块复用。",
            "collaboration": "向密码管理提供 passwordstart 等输入；向内容生成子系统提供 extracted_style、core_points、reference_demo、product_output、topic、articlecount、requirements、index；向校验子系统提供原始需求/限制用于对照。"
        },
        {
            "name": "密码/口令管理",
            "contained_modules": ["COMPUTE_PASS", "ASSEMBLE_PASS", "CHECK_PS"],
            "responsibility": "计算循环次数和口令数字并构建完整口令形式，确保生成时能正确且合规地插入口令。",
            "independence": "口令计算为 one-shot 技能，依赖少量输入并输出简单参数（assembled_pass、pass_position_constraints），不需要关心正文生成或最终校验的细节。",
            "collaboration": "从输入与预处理接收 passwordstart 等原始输入；向内容生成子系统输出 assembled_pass、循环次数与口令插入约束；在异常情况下向校验与回退报告错误以触发回退。"
        },
        {
            "name": "内容生成循环",
            "contained_modules": ["TITLE_GEN", "DRAFT", "ADJUST"],
            "responsibility": "基于风格、核心点与口令约束生成标题与正文草稿，并在不通过时进行修正迭代直至初步通过。",
            "independence": "专注于将结构化输入合并为候选文本，生成逻辑与校验规则分离，校验结果作为明确接口驱动本地调整，不直接承担规则判断责任。",
            "collaboration": "接收来自输入与预处理的 extracted_style、core_points、reference_demo、product_output、topic、articlecount、requirements、index；接收来自密码管理的 assembled_pass 与插入约束；向校验与回退发送 candidate_title、candidate_draft、emoji、口令位置等以获取 validate_result 与 failure_reasons；根据校验结果（fail+reasons）在 ADJUST 中迭代。"
        },
        {
            "name": "校验与回退",
            "contained_modules": ["VALIDATE", "FINAL", "FALLBACK", "END"],
            "responsibility": "对候选标题与正文进行合规性校验（长度/违禁词/话题/emoji/口令位置/品牌约束），决定通过并输出最终结果或在异常时触发回退/错误提示并结束流程。",
            "independence": "校验为规则/策略集合，输出明确的通过/失败结论与原因，生成模块只需依据这些结论调整或结束，规则可以独立扩展或替换而不影响生成或口令逻辑。",
            "collaboration": "从内容生成子系统接收 candidate_title、candidate_draft、assembled_pass 插入点、emoji 列表及其它元数据；返回 validate_result（pass/fail）与 failure_reasons；在失败且不可调整（超限/信息缺失）时输出回退信息并结束流程（FALLBACK -> END）；在通过时输出 FINAL（最终合规的标题+正文）。"
        }
    ]
}
    '''
    sub_prompt_messages.append({"role": "user", "content": '<<<初始提示词：\n' + user_input + '\n用户初始提示词结束>>>\n\n' + subsystems})
    sub_prompts = llm_client.call(sub_prompt_messages, "gpt-5-mini")
    print(sub_prompts)
'''

'''