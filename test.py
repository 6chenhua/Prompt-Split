def split_text_by_length(text: str, chunk_size: int = 800):
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
if __name__ == '__main__':
    from extract_variable import read_file
    nl = read_file('nl_prompt.txt')
    cs = split_text_by_length(nl)
    for c in cs:
        print(c)
        print('='*100)