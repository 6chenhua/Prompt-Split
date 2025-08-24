import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from LLMTool import LLMApiClient

# API配置
MODEL = "gpt-5-mini"
llm_client = LLMApiClient()

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def split_text_by_length(text: str, chunk_size: int = 500):
    """
    根据指定长度切割文本。
    在寻找切割点时，会向后寻找最近的非空行，确保每段文本的完整性。
    """
    if not isinstance(text, str):
        raise TypeError("输入必须是字符串类型。")
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正数。")

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # 检查切割点是否需要调整
        if end < text_length:
            # 向后寻找最近的空行（连续两个换行符）作为切割点
            next_paragraph_break = text.find('\n\n', end)

            if next_paragraph_break != -1:
                end = next_paragraph_break + 2  # 包含两个换行符
            else:
                # 如果找不到空行分隔，就向后寻找最近的非空换行符
                next_newline = text.find('\n', end)
                if next_newline != -1:
                    # 找到换行符后，继续寻找下一个非空行
                    while next_newline != -1:
                        # 判断换行符后是否为空行或只包含空白字符
                        if text[next_newline + 1:].strip():
                            # 如果下一行不为空，则将切割点设为当前换行符之后
                            end = next_newline + 1
                            break
                        else:
                            # 如果下一行为空，则继续向后寻找下一个换行符
                            next_newline = text.find('\n', next_newline + 1)
                    # 如果找不到非空行，则将切割点设为文本末尾
                    if next_newline == -1:
                        end = text_length
                else:
                    # 找不到任何换行符，直接切割到文本末尾
                    end = text_length

        chunks.append(text[start:end])
        start = end

    # 移除空字符串，这可能发生在文本以换行符结尾时
    return [chunk for chunk in chunks if chunk.strip()]


def call_llm(chunk, idx):
    """调用 LLM 处理单个分块（使用http.client）"""
    print(f"--- input chunk {idx} ---\n{chunk}\n")
    try:
        # 读取系统提示并替换占位符
        sys_prompt = read_file('extract_var_v6.txt')
        # sys_prompt = sys_prompt.replace("{在此粘贴原文}", chunk)
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": chunk},
        ]
        content = llm_client.call(messages)

        return idx, content

    except Exception as e:
        print(f"处理出错 (idx: {idx}): {str(e)}")
        return idx, ""


def extract_variables_from_json(json_str: str):
    """从 LLM 返回的 JSON 字符串中提取所有变量名"""
    if not json_str:
        return []

    # 使用正则表达式匹配并提取 JSON 数组部分
    match = re.search(r'\[.*?\]', json_str, re.DOTALL)
    if not match:
        return []

    try:
        # 解析匹配到的 JSON 字符串
        json_array = json.loads(match.group(0))
        # 提取每个字典中的 'text' 字段内容
        variable_names = [item['text'] for item in json_array if 'text' in item]
        return variable_names
    except json.JSONDecodeError as e:
        print(f"解析JSON失败: {e}")
        return []


def process_chunks_concurrently(chunks: list[str], max_workers: int = 5):
    """使用多线程并发处理文本分块，并从 LLM 回复中提取变量名"""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(call_llm, chunk, i) for i, chunk in enumerate(chunks)]

        for future in as_completed(futures):
            idx, result_str = future.result()
            print(f"--- result {idx} ---\n{result_str}\n")
            if result_str:
                results[idx] = extract_variables_from_json(result_str)
            else:
                results[idx] = []

    # 保证输出顺序和输入顺序一致
    ordered_results = [results[i] for i in sorted(results.keys())]

    # 扁平化列表并去重
    all_variable_names = [name for sublist in ordered_results for name in sublist]
    return list(set(all_variable_names))

def post_process(nl_with_var):
    prompt = read_file('post_process_variable_v2.txt').replace("{{prompt_with_var}}", nl_with_var)
    messages = [
        {"role": "system", "content": prompt}
    ]
    res = llm_client.call(messages)
    json_str = llm_client.extract_json_string(res)
    processed_nl = json.loads(json_str)['cleaned_text']
    return processed_nl

if __name__ == '__main__':
    p0 = read_file('nl_prompt.txt')
    chunks = split_text_by_length(p0)
    # for c in chunks:
    #     print(c)
    #     print('='*100)
    outputs = process_chunks_concurrently(chunks)
    # outputs = ['精准匹配', '正常数据', '客户情绪', '产品', '周期范围', '互动中位数', '近60天笔记数小于10篇', '仅展示蒲公英达人', '特殊字段要求', '客户继续不填写', '{{userClasss}}', '内容方向完全符合要求', '模板必须按以下格式输出', 'CPM(曝光单价)', '客户是否需要精准匹配', '排竞时间', '客户话题', '达人地域', '年轻', '自我介绍', '是否全部开启还是指定部分', '客户', '人设定位', '是否开启竞品限制要求', '数据太水', '排除竞品投放过达人', '竞品限制条件', '品牌', '需求模板', '排除官方账号', '达人性别', '单个预算要求', '粉丝人群条件', '是否排竞', '太水的标准', '年轻的年龄区间', '评估维度', '自我介绍只执行一次', '刷数据', '匹配需求条件', 'CPC(阅读单价)', '排除蓝V账号', '投放周期', '是否开启投放周期', '近期爆文数', '允许选择多个内容方向', '达人要求条件', '客户继续不回复', '已获取筛选账户需求', '情感投入程度', '投放总预算', '{{talk_data}}', '首次交流', '近30日粉丝量下降博主', '粉丝活跃度占比', '是否需要先建联再提报', '博主最新微信消息', '自我介绍次数限制', '基础需求信息', '客户情感倾向', '客户称呼', '细分标签', '是否开启粉丝人群条件', '是否开启达人要求条件', '同个问题只允许询问一次', '本次提报数量', '未填写的需求信息', '是否开启特殊字段要求', '是否开启数据表现要求', '投放形式', '筛选账户需求', '避免相似回答', '内容方向', '剔除近期已合作博主', '聊天信息', '追加需求条件', '需求模板格式', '每个条件都需要换行展示', '模糊匹配达人', '数据表现要求', '仅展示竞品投放过达人', '意向达人', '其他特殊字段要求', '客户输入内容', '粉丝年龄占比', '粉丝数', '聊天记录', '达人调性', '禁止向客户透露以上信息', '回复语气', '需求是否有疑问', '竞品名称', '首次与客户交流', '达人参考链接', '需求确认模板', '数据量级', 'CPE(互动单价)', '客户已发过需求', '{{input}}', '宝子', '追加需求信息', '假数据', '阅读中位数', '粉丝性别占比', '客户产品相关问题', '性价比高', '账号类型', '配色好看']
    print(outputs)
    for v in outputs:
        p0 = p0.replace(v, "{"+v+"}")
    print(p0)

    nl_with_var = read_file('nl_prompt.md')
    pl = post_process(p0)
    print(pl)


