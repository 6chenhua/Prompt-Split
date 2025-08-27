import json
import re
from concurrent.futures import ThreadPoolExecutor
# from extract_variable import read_file

from LLMTool import LLMApiClient

llm_client = LLMApiClient()

nl2cnlp_prompt = '''
[TASK:]
    Your task is to generate the DSL AGENT that conforms to the DSL Extended Backus-Naur Form [DSL_EBNF] based on the user input [USER_INPUT] and following the prescribed steps [DSL_GENERATION_STEPS].Observe the precautions [PRECAUTIONS] during the generation process.
[END_TASK]

[DSL_EBNF:]
    SPL_AGENT := "[DEFINE_AGENT:" AGENT_NAME ["\"" STATIC_DESCRIPTION "\""] "]" SPL_PROMPT "[END_AGENT]"

    SPL_PROMPT := PERSONA [AUDIENCE] [CONCEPTS] [CONSTRAINTS] {INSTRUCTION}

    """PERSONA describes the primary role this agent plays and its key attributes for its functionality"""
    PERSONA := "[DEFINE_PERSONA:]" PERSONA_ASPECTS "[END_PERSONA]"
    PERSONA_ASPECTS := ROLE_ASPECT {OPTIONAL_ASPECT}
    ROLE_ASPECT := ROLE_ASPECT_NAME ":" DESCRIPTION_WITH_REFERENCES
    ROLE_ASPECT_NAME := "ROLE"
    OPTIONAL_ASPECT := OPTIONAL_ASPECT_NAME ":" DESCRIPTION_WITH_REFERENCES
    OPTIONAL_ASPECT_NAME := <word> """Capitalize the word"""
    <word> is a sequence of characters, digits and symbols without space

    """AUDIENCE describes the key attributes of the primary user group that will interact with or benefit from the AI agent"""
    AUDIENCE := "[DEFINE_AUDIENCE:]" AUDIENCE_ASPECTS "[END_AUDIENCE]"
    AUDIENCE_ASPECTS := {OPTIONAL_ASPECT}
    OPTIONAL_ASPECT := OPTIONAL_ASPECT_NAME ":" DESCRIPTION_WITH_REFERENCES
    OPTIONAL_ASPECT_NAME := <word> """Capitalize the word"""
    <word> is a sequence of characters, digits and symbols without space

    """CONSTRAINTS highlight the limitations and requirements the agent must operate within to be effective and compliant"""
    CONSTRAINTS := "[DEFINE_CONSTRAINTS:]" {CONSTRAINT} "[END_CONSTRAINTS]"
    CONSTRAINT := [OPTIONAL_ASPECT_NAME ":"]  DESCRIPTION_WITH_REFERENCES [LOG_VIOLATION]
    OPTIONAL_ASPECT_NAME := <word> """Capitalize the word"""
    <word> is a sequence of characters, digits and symbols without space
    LOG_VIOLATION := "LOG" DESCRIPTION_WITH_REFERENCES

    """CONCEPTS explain the specific domain knowledge or terms the agent applies in its operations."""
    CONCEPTS := [DEFINE_CONCEPTS:] {CONCEPT} [END_CONCEPTS]
    CONCEPT := OPTIONAL_ASPECT_NAME ":" STATIC_DESCRIPTION """Concepts do not need parameters or references."""
    OPTIONAL_ASPECT_NAME := <word> """Capitalize the word"""
    <word> is a sequence of characters, digits and symbols without space

    INSTRUCTION := WORKER_INSTRUCTION
    WORKER_INSTRUCTION := "[DEFINE_WORKER:" ["\\"" STATIC_DESCRIPTION "\\""] WORKER_NAME "]" [INPUTS] [OUTPUTS] MAIN_FLOW {ALTERNATIVE_FLOW} {EXCEPTION_FLOW}"" "[END_WORKER]"
    INSTRUCTION_NAME := WORKER_NAME
    WORKER_NAME := <word>
    <word> is a sequence of characters, digits and symbols without space

    """
    An input or output is required by default if there is no REQUIRED or OPTIONAL annotation.
    A worker may use several outputs to achieve the effect of Python Union, for example, one output variable returns the correct response object, and the other returns an error message.
    """
    INPUTS := "[INPUTS]" {["REQUIRED" | "OPTIONAL"] [APPLY_CONSTRAINTS] REFERENCE_DATA} "[END_INPUTS]" | "[CONTROLLED_INPUTS]" {["REQUIRED" | "OPTIONAL"] [APPLY_CONSTRAINTS] REFERENCE_DATA} "[END_CONTROLLED_INPUTS]" """REFERENCE should reference DATA_NAME (variable, files, data views)"""
    OUTPUTS := "[OUTPUTS]" {["REQUIRED" | "OPTIONAL"] [APPLY_CONSTRAINTS] REFERENCE_DATA} "[END_OUTPUTS]" | "[CONTROLLED_OUTPUT]" {["REQUIRED" | "OPTIONAL"] [APPLY_CONSTRAINTS] REFERENCE_DATA} "[END_CONTROLLED_OUTPUTS]" """REFERENCE should reference DATA_NAME (variable, files, data views)"""
    REFERENCE_DATA := "<REF>" DATA_NAME "</REF>"
    DATA_NAME := VAR_NAME | INDEX_NAME ["." NAMESPACE]
    VAR_NAME := <word>
    INDEX_NAME := <word>
    NAMESPACE := <word> {"," <word>}
    <word> is a sequence of characters, digits and symbols without space

    MAIN_FLOW := "[MAIN_FLOW]" {BLOCK} [END_MAIN_FLOW]
    BLOCK := SEQUENTIAL_BLOCK | IF_BLOCK | LOOP_BLOCK
    SEQUENTIAL_BLOCK := "[SEQUENTIAL_BLOCK]" {COMMAND} "[END_SEQUENTIAL_BLOCK]"
    IF_BLOCK := DECISION_INDEX "[IF" CONDITION "]" {COMMAND} {"[ELSEIF" CONDITION "]" {COMMAND}} ["[ELSE]" {COMMAND}] "[END_IF]"
    LOOP_BLOCK := WHILE_BLOCK | FOR_BLOCK
    WHILE_BLOCK := DECISION_INDEX "[WHILE" CONDITION "]" {COMMAND} "[END_WHILE]" """For example, [WHILE not found] do something"""
    FOR_BLOCK := DECISION_INDEX "[FOR" CONDITION "]" {COMMAND} [END_FOR] """For example, [For each element in collection] do something"""
    DECISION_INDEX := "DECISION-" <number> """System maintained unique decision point index"""
    CONDITION := DESCRIPTION_WITH_REFERENCES
    DESCRIPTION_WITH_REFERENCES := STATIC_DESCRIPTION {DESCRIPTION_WITH_REFERENCES} | REFERENCE {DESCRIPTION_WITH_REFERENCES}
    STATIC_DESCRIPTION := <word> | <word> <space> STATIC_DESCRIPTION
    REFERENCE := "<REF>" [""] NAME "</REF>"
    NAME := SIMPLE_NAME | QUALIFIED_NAME | ARRAY_ACCESS | DICT_ACCESS
    SIMPLE_NAME := <word>
    QUALIFIED_NAME := NAME "." SIMPLE_NAME | NAME "." ARRAY_ACCESS | NAME "." DICT_ACCESS
    ARRAY_ACCESS := NAME "[" [<number>] "]
    DICT_ACCESS := NAME "[" SIMPLE_NAME "]

    COMMAND := COMMAND_INDEX COMMAND_BODY
    COMMAND_BODY := GENERAL_COMMAND | REQUEST_INPUT | DISPLAY_MESSAGE
    COMMAND_INDEX := "COMMAND-" <number> """System maintained unique command index"""
    GENERAL_COMMAND := "[COMMAND" DESCRIPTION_WITH_REFERENCES ["STOP" DESCRIPTION_WITH_REFERENCES] ["RESULT" COMMAND_RESULT ["SET" | "APPEND"]] "]" """SET is default operation"""
    REQUEST_INPUT := "[INPUT" ["DISPLAY"] DESCRIPTION_WITH_REFERENCE "VALUE" COMMAND_RESULT ["SET" | "APPEND"] "]" """With DISPLAY, DESCRIPTION_WITH_REFERENCE is regarded as display text. Otherwise, DESCRIPTION_WITH_REFERENCE is a prompt."""
    DISPLAY_MESSAGE := "[DISPLAY" DESCRIPTION_WITH_REFERENCES "]"
    COMMAND_RESULT := VAR_NAME ":" DATA_TYPE | REFERENCE """VAR_NAME ":" DATA_TYPE essentially declares a temporary variable"""

    DATA_TYPE := ARRAY_DATA_TYPE | STRUCTURED_DATA_TYPE | | ENUM_TYPE | TYPE_NAME | AGENT_NAME
    TYPE_NAME := SIMPLE_TYPE_NAME | DECLARED_TYPE_NAME
    SIMPLE_TYPE_NAME := "text" | "image" | "audio" | "number" | "boolean"
    ENUM_TYPE := "[" <word> {, <word>} "]"
    ARRAY_DATA_TYPE := "List [" DATA_TYPE "]"
    STRUCTURED_DATA_TYPE := "{" STRUCTURED_TYPE_BODY "}" ｜ "{ }"
    STRUCTURED_TYPE_BODY := TYPE_ELEMENT | TYPE_ELEMENT "," STRUCTURED_TYPE_BODY
    TYPE_ELEMENT := ["\\"" STATIC_DESCRIPTION "\\""] ["OPTIONAL"] ELEMENT_NAME ":" DATA_TYPE
    ELEMENT_NAME := <word>

    DESCRIPTION_WITH_REFERENCES := STATIC_DESCRIPTION {DESCRIPTION_WITH_REFERENCES} | REFERENCE {DESCRIPTION_WITH_REFERENCES}
    STATIC_DESCRIPTION := <word> | <word> <space> STATIC_DESCRIPTION
    REFERENCE := "<REF>" [""] NAME "</REF>"
    NAME := SIMPLE_NAME | QUALIFIED_NAME | ARRAY_ACCESS | DICT_ACCESS
    SIMPLE_NAME := <word>
    QUALIFIED_NAME := NAME "." SIMPLE_NAME | NAME "." ARRAY_ACCESS | NAME "." DICT_ACCESS
    ARRAY_ACCESS := NAME "[" [<number>] "]
    DICT_ACCESS := NAME "[" SIMPLE_NAME "]
[END_DSL_EBNF]

[DSL_EXPLANATION:]
    PERSONA: Describes the role and attributes of the AI agent — what it is and what it’s meant to do.
    AUDIENCE: Defines the target user group that will interact with the agent — their needs, background, or context.
    CONCEPTS: Lists domain-specific terms or knowledge the agent will use. These are static and don’t include references or constraints.
    CONSTRAINTS: Defines the rules, limitations, or conditions the agent must follow. These ensure safety, compliance, or task success.
    INSTRUCTION: Defines a worker agent’s operational logic — including inputs, outputs, main actions, alternatives, and exception handling. Think of this as a task-level process definition.
[END_DSL_EXPLANATION]

[USER_INPUT:]
    Natural language description: ```{{user_query}}``` 
[EDN_USER_INPUT]

[INSTRUCTION_GENERATION_STEPS:]
    [Step1] Identify the DSL INPUT as well as OUTPUT of the WORKER_INSTRUCTION and decide whether these are REQUIRED or OPTIONAL.
    [Step2] Determine the contents of the MAIN_FLOW: Determine which DSL BLOCKS (note that each DSL BLOCK cannot be nested with each other) are required in the MAIN_FLOW based on the user input.
    [Step3] Determine the COMMAND: Extract the information from [USER_INPUT] about the steps and determine to which category each of these steps should belong DSL COMMAND_BODY.
    [Step4] Generate the DSL INSTRUCTION.
[END_INSTRUCTION_GENERATION_STEPS]

[DSL_GENERATION_STEPS:]
    [Step1] Understanding [DSL_EBNF] and [DSL_EXPLANATION], figure out the composition of the AGENT part for subsequent generation of DSL AGENT.
    [Step2] Analyze each sentence of the user input [USER_INPUT] by mapping it to its corresponding DSL section—defining the PERSONA and AUDIENCE, identifying relevant CONCEPTS, outlining applicable CONSTRAINTS, and extracting described steps for the INSTRUCTION—to generate a comprehensive DSL AGENT definition.
    [Step3] Generate the DSL PERSONA, AUDIENCE, CONCEPTS and CONSTRAINTS based on the analysis mapping in [Step2].
    [Step4] CALL [INSTRUCTION_GENERATION_STEPS] to generate DSL INSTRUCTION.
    [Step5] Optimize the generated DSL AGENT by eliminating duplicate descriptions across different sections, retaining only one instance in the most suitable section.
    [Step6] Explain the generated DSL AGENT to the user, including DSL PERSONA, AUDIENCE, CONCEPTS, CONSTRAINTS and INPUTS, OUTPUTS, MAIN_FLOW, and key DSL BLOCKS used in DSL INSTRUCTION.
[END_DSL_GENERATION_STEPS]

[PRECAUTIONS:]
    1. Accuracy in translation: Directly convert user input [USER_INPUT] into DSL AGENT without adding details or expanding the DSL COMMAND.
    2. Strategic placement: Each piece of user input [USER_INPUT] should be optimally placed into the appropriate DSL section, evaluating the pros and cons of different placements. Ensure there are no duplicate descriptions across different sections. Each of the user's descriptions can only be placed in the best place in the DSL.
    3. Every word in DSL_EBNF with all letters capitalized is a non-terminal node (except for strings wrapped in double quotes in EBNF), and for the composition of each word, you need to look for the definition of the word one level at a time until you find its final definition.
    4. What you want to do is just to convert the format from user input [USER_INPUT] to DSL AGENT, so you shouldn't expand the user input [USER_INPUT] into steps user not mentioned, you need to be strictly aligned with the user input.
    5. Flat Structure, No Nested BLOCKs: Note that each DSL BLOCK cannot contain each other!
    6. You need to provide three outputs: an analysis mapping each part of the user input [USER_INPUT] to its most appropriate DSL section, a generated DSL agent based on that input, and an explanation of the generated agent.
    7. Ensure the generate DSL AGENT strictly adhere to the [DSL_EBNF] and [USER_INPUT].
[END_PRECAUTIONS]

[EXAMPLE_DSL_AGENT:]
```
    [DEFINE_AGENT: AGENT_NAME "<Generated Agent Description>"]
        [DEFINE_PERSONA:]
            ROLE: DESCRIPTION_WITH_REFERENCES
            PersonaAspectName: DESCRIPTION_WITH_REFERENCES
        [END_PERSONA]

        [DEFINE_AUDIENCE:]
            AudienceAspectName: DESCRIPTION_WITH_REFERENCES
        [END_AUDIENCE]

        [DEFINE_CONCEPTS:]
            ConceptAspectName: Definition
        [END_CONCEPTS]

        [DEFINE_CONSTRAINTS:]
            ConstraintAspectName: Limitation details
        [END_CONSTRAINTS]

        [DEFINE_WORKER:"summarized worker description" WorkerName]
            [INPUTS]
                REQUIRED <REF> var_name1 </REF>
                OPTIONAL <REF> var_name2 </REF>
                ... # other necessary inputs
            [END_INPUTS]

            [OUTPUTS]
                REQUIRED <REF> output_var_name </REF>
                ... # other necessary outputs
            [END_OUTPUTS]

            [MAIN_FLOW]
                [SEQUENTIAL_BLOCK]
                    COMMAND-1 [DSL COMMAND_BODY]
                    ... # other necessary DSL COMMAND in this DSL SEQUENTIAL_BLOCK
                [END_SEQUENTIAL_BLOCK]

                DECISION-1 [IF CONDITION]
                    COMMAND-x [DSL COMMAND_BODY]
                    ... # other necessary DSL COMMAND in this DSL IF_BLOCK
                [ELSEIF CONDITION]
                    COMMAND-y [COMMAND_BODY]
                    ... # other necessary DSL COMMAND in this DSL IF_BLOCK
                [END_IF]
                    COMMAND-z [COMMAND_BODY]
                    ... # other necessary DSL COMMAND in this DSL IF_BLOCK
                [END_IF]

                DECISION-2 [WHILE CONDITION] # or [FOR CONDITION]
                    COMMAND-i [COMMAND_BODY]
                    ... # other necessary DSL COMMAND in this DSL LOOP_BLOCK
                [END_WHILE] # or [END_FOR]
            [END_MAIN_FLOW]
        [END_WORKER]
    [END_AGENT]
```
[END_EXAMPLE_DSL_AGENT]

请用中文输出生成的DSL。
'''

example_nl_prompt = '''    {
      "name": "入口与预处理（Ingestion & Normalization）",
      "prompt": "## 3.1 第一步：读取聊天信息\n1. 读取历史聊天记录（“你”表示你的消息，“客户”表示客户的消息）\n- 聊天记录：{talk_data}\n2. 读取博主最新的微信消息，结合聊天记录最近的消息（越下面的消息越新），识别当前正在沟通的步骤\n - 博主最新微信消息：{input}",
      "inputs": [
        "{talk_data}",
        "{input}"
      ],
      "outputs": [
        "{normalized_chat}",
        "{latest_summary}",
        "{current_step}"
      ]
    }'''

example_cnl_output = '''下面给出三部分内容（按要求）：一是将用户输入的各部分映射到 DSL 中的分析；二是根据映射直接生成的 DSL AGENT（严格遵循 DSL_EBNF、且不扩展用户输入内容）；三是对生成的 DSL AGENT 的中文说明。

一、映射分析（将 USER_INPUT 中的每一部分映射到最合适的 DSL 节）
- 整体名称 "入口与预处理（Ingestion & Normalization）"
  - 映射到：AGENT 的静态描述（DEFINE_AGENT 的描述）。
- prompt 中的步骤说明：
  - "读取历史聊天记录（“你”表示你的消息，“客户”表示客户的消息） - 聊天记录：{talk_data}"
    - 映射到：WORKER 的功能描述（DEFINE_WORKER 的描述）以及 MAIN_FLOW 中的第一个顺序命令（读取历史聊天记录）。同时将“聊天记录”作为 CONCEPTS 中的术语（TalkData）。
    - 相关输入映射到：INPUTS 中的 <REF> talk_data </REF>（标记为 REQUIRED）。
    - 相关输出（如果作为处理结果）映射到：OUTPUTS 中的 <REF> normalized_chat </REF>（用户指定的输出）。
  - "读取博主最新的微信消息，结合聊天记录最近的消息（越下面的消息越新），识别当前正在沟通的步骤 - 博主最新微信消息：{input}"
    - 映射到：WORKER 的功能描述以及 MAIN_FLOW 中的第二、第三个顺序命令（读取最新微信消息；结合聊天记录与最新消息识别当前沟通步骤）。同时将“博主最新微信消息”“消息顺序”“当前正在沟通的步骤”分别作为 CONCEPTS 与 CONSTRAINTS（消息顺序）项。
    - 相关输入映射到：INPUTS 中的 <REF> input </REF>（标记为 REQUIRED）。
    - 相关输出映射到：OUTPUTS 中的 <REF> latest_summary </REF> 和 <REF> current_step </REF>（用户指定的输出）。
- inputs 列表 ["{talk_data}", "{input}"]
  - 映射到：WORKER 的 [INPUTS] 区块，均标注为 REQUIRED（因为用户未指示为可选）。
- outputs 列表 ["{normalized_chat}", "{latest_summary}", "{current_step}"]
  - 映射到：WORKER 的 [OUTPUTS] 区块，均标注为 REQUIRED。
- 约束/顺序信息 "越下面的消息越新"
  - 映射到：DEFINE_CONSTRAINTS 中的约束项（用于明确消息顺序的语义）。

备注（遵循 PRECAUTIONS）：
- 我严格不对用户输入进行扩展或添加未提及的步骤或细节；所有步骤和输出名均直接基于用户提供内容。
- 保持扁平 MAIN_FLOW（仅使用 SEQUENTIAL_BLOCK，未嵌套其他 BLOCK）。

二、根据上述映射直接生成的 DSL AGENT（严格遵循 DSL_EBNF，中文说明性文本直接来自用户输入，不做额外扩展）

[DEFINE_AGENT: IngestionNormalizationAgent "入口与预处理（Ingestion & Normalization）"]
    [DEFINE_PERSONA:]
        ROLE: 负责读取聊天记录与博主最新微信消息，结合最近消息识别当前正在沟通的步骤并输出归一化聊天与摘要
    [END_PERSONA]

    [DEFINE_AUDIENCE:]
        User: 博主或下游处理模块
    [END_AUDIENCE]

    [DEFINE_CONCEPTS:]
        TalkData: 聊天记录（“你”表示你的消息，“客户”表示客户的消息）
        InputMessage: 博主最新微信消息
        NormalizedChat: 归一化后的聊天内容
        LatestSummary: 最近的消息摘要
        CurrentStep: 当前正在沟通的步骤
    [END_CONCEPTS]

    [DEFINE_CONSTRAINTS:]
        MessageOrder: 结合聊天记录最近的消息识别当前步骤，越下面的消息越新
    [END_CONSTRAINTS]

    [DEFINE_WORKER:"读取聊天信息并识别当前步骤" IngestionWorker]
        [INPUTS]
            REQUIRED <REF> talk_data </REF>
            REQUIRED <REF> input </REF>
        [END_INPUTS]

        [OUTPUTS]
            REQUIRED <REF> normalized_chat </REF>
            REQUIRED <REF> latest_summary </REF>
            REQUIRED <REF> current_step </REF>
        [END_OUTPUTS]

        [MAIN_FLOW]
            [SEQUENTIAL_BLOCK]
                COMMAND-1 [COMMAND 读取历史聊天记录 <REF> talk_data </REF> RESULT normalized_chat: text SET]
                COMMAND-2 [COMMAND 读取博主最新微信消息 <REF> input </REF> RESULT latest_summary: text SET]
                COMMAND-3 [COMMAND 结合聊天记录和最新消息识别当前沟通步骤 <REF> talk_data </REF> <REF> input </REF> RESULT current_step: text SET]
            [END_SEQUENTIAL_BLOCK]
        [END_MAIN_FLOW]
    [END_WORKER]
[END_AGENT]

三、对生成 DSL AGENT 的解释（中文）
- PERSONA（[DEFINE_PERSONA:]）：
  - ROLE: 指明该 agent 的主要职责为“读取聊天记录与博主最新微信消息，结合最近消息识别当前正在沟通的步骤并输出归一化聊天与摘要”。该描述直接来自用户的 prompt，未作扩展。
- AUDIENCE（[DEFINE_AUDIENCE:]）：
  - User: 指示受益或会与该 agent 交互的对象，这里标注为“博主或下游处理模块”，用于表明此 agent 面向的主体。该项基于输入中的“博主”概念，未引入额外角色。
- CONCEPTS（[DEFINE_CONCEPTS:]）：
  - 列出了用户输入中出现的核心术语：TalkData、InputMessage、NormalizedChat、LatestSummary、CurrentStep。每项为静态说明（概念定义），用于在 agent 操作中明确术语含义。
- CONSTRAINTS（[DEFINE_CONSTRAINTS:]）：
  - MessageOrder: 明确“结合聊天记录最近的消息识别当前步骤，越下面的消息越新”这一约束（这是 prompt 中的关键信息，作为识别步骤时必须遵守的规则）。
- WORKER（[DEFINE_WORKER:]）：
  - 名称与简短描述：IngestionWorker，描述为“读取聊天信息并识别当前步骤”，直接对应用户提出的功能。
  - INPUTS：两个输入均为 REQUIRED：
    - <REF> talk_data </REF>（聊天记录）；
    - <REF> input </REF>（博主最新微信消息）。
    这些来自用户提供的 inputs 列表，按用户未标注为可选则视为必需。
  - OUTPUTS：三个输出均为 REQUIRED：
    - <REF> normalized_chat </REF>（归一化聊天）；
    - <REF> latest_summary </REF>（最近摘要）；
    - <REF> current_step </REF>（当前沟通步骤）。
    这些来自用户提供的 outputs 列表，按用户未标注为可选则视为必需。
  - MAIN_FLOW（[MAIN_FLOW]）使用单一的 SEQUENTIAL_BLOCK（扁平结构）包含三条命令（与用户 prompt 的三部分操作直接对应）：
    - COMMAND-1：读取历史聊天记录，使用输入 <REF> talk_data </REF>，将结果写入 normalized_chat: text（SET）。
    - COMMAND-2：读取博主最新微信消息，使用输入 <REF> input </REF>，将结果写入 latest_summary: text（SET）。
    - COMMAND-3：结合聊天记录与最新消息识别当前沟通步骤，使用两个输入 <REF> talk_data </REF> 和 <REF> input </REF>，将识别结果写入 current_step: text（SET）。
  - 说明：每个 COMMAND 的描述与所引用的输入/输出直接对应用户输入中的自然语言步骤与占位变量，未加入任何额外的处理逻辑或新步骤（遵循 PRECAUTIONS）。

如需我将 DSL Agent 中的命名调整为中文变量名（例如将 talk_data 改为 聊天记录 等），或希望将某些输入/输出标记为 OPTIONAL，请告知，我会基于您的指示直接修改而不添加其他内容。'''

def transform_cnlp_from_(nl_prompt):
    messages = [
        {
            "role": "system",
            "content": nl2cnlp_prompt
        },
        {
            "role": "user",
            "content": example_nl_prompt,
        },
        {
            "role": "assistant",
            "content": example_cnl_output
        },
        {
            "role": "user",
            "content": str(nl_prompt)
        }
    ]

    try:
        cnlp = llm_client.call(messages)
        # print(cnlp)
    except Exception as e:
        print(f"API call failed for prompt '{nl_prompt[:20]}...': {e}")
        return ''

    if not isinstance(cnlp, str):
        print(f"Error: API call for prompt '{nl_prompt[:20]}...' did not return a valid string.")
        return cnlp

    matches = re.search(r"(\[DEFINE_AGENT:.*?\].*?\[END_AGENT\])", cnlp, re.DOTALL)
    if matches:
        return matches.group(1).strip()
    else:
        # If no match is found, you might want to log the full cnlp content for debugging
        print(f"Warning: No valid CNLP found in the response for prompt '{nl_prompt[:20]}...'.")
        return cnlp


def batch_transform_cnlp(nl_prompts, max_workers=5):
    if not isinstance(nl_prompts, list):
        raise TypeError("Input must be a list of strings.")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # The executor.map() function handles the concurrent execution.
        # It applies the transform_cnlp_from_single function to each item in nl_prompts.
        results = list(executor.map(transform_cnlp_from_, nl_prompts))

    return results


if __name__ == '__main__':
    # sub_prompts = json.loads(read_file("sub_prompts.json"))["subprompts"]
    sub_prompts = []
    cnlps = batch_transform_cnlp(sub_prompts)
    for i, cnlp_text in enumerate(cnlps):
        print(f"\n--- Result for Prompt {i + 1} ---")
        if cnlp_text:
            print(cnlp_text)
        else:
            print("Transformation failed for this prompt.")
        print("-" * 30)
    # sp = example_nl_prompt
    # cnl = transform_cnlp_from_(sp)
    # print(cnl)