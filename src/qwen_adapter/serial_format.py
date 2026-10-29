"""Opt-in Qwen function format; strict local adaptation, not Qwen-Agent execution.

Format reference: https://qwen.readthedocs.io/en/v2.5/framework/function_call.html
No output healing, parallel batches, or synthetic observations.
"""
import json

INTERFACE = 'qwen_serial_v1'
STOPS = ('✿RESULT✿', '✿RETURN✿')
FORMAT = """# Tools
## You have access to the following tools:

{descriptions}

## When you need to call a tool, please insert the following command in your reply, which can be called zero or multiple times according to your needs:
✿FUNCTION✿: The tool to use, should be one of [{names}]
✿ARGS✿: The input of the tool
✿RESULT✿: Tool results
✿RETURN✿: Reply based on tool results. Images need to be rendered as ![](url)"""


def render_prompt(messages, tools):
    """Render ChatML with tool observations inside the open assistant turn.

    Preserve text, including continuation-leading spaces. Only one pending action
    is allowed, matched by ID before a result is inserted.
    """
    descriptions = []
    names = []
    for tool in tools:
        f = tool['function']
        names.append(f['name'])
        descriptions.append('### ' + f['name'] + '\n\n' + f['name'] + ': ' +
                            f['description'] + ' Parameters: ' +
                            json.dumps(f['parameters'], ensure_ascii=False) +
                            ' Format the arguments as a JSON object.')
    if names != ['execute_command']:
        raise ValueError('Serial format requires execute_command only')
    if not messages or messages[0]['role'] != 'system':
        raise ValueError('Expected system-first history')
    system = messages[0]['content'] + '\n\n' + FORMAT.format(
        descriptions='\n\n'.join(descriptions), names=','.join(names))
    prompt = '<|im_start|>system\n' + system + '<|im_end|>'
    open_assistant = False
    pending = None
    after_result = False
    for m in messages[1:]:
        role = m['role']
        if role == 'user':
            if pending:
                raise ValueError('Missing tool result')
            if open_assistant:
                prompt += '<|im_end|>'
            prompt += '\n<|im_start|>user\n' + m['content'] + '<|im_end|>'
            open_assistant = False
            after_result = False
        elif role == 'assistant':
            if pending:
                raise ValueError('Missing tool result')
            if not open_assistant:
                prompt += '\n<|im_start|>assistant\n'
                open_assistant = True
            elif after_result:
                prompt += ': '
            prompt += m.get('content') or ''
            calls = m.get('tool_calls', [])
            if calls:
                if len(calls) != 1 or calls[0]['function']['name'] != 'execute_command':
                    raise ValueError('Expected one execute_command call')
                f = calls[0]['function']
                args = f['arguments']
                if isinstance(args, str):
                    args = json.loads(args)
                if not isinstance(args, dict):
                    raise ValueError('History arguments must be an object')
                if m.get('content'):
                    prompt += '\n'
                prompt += '✿FUNCTION✿: execute_command\n✿ARGS✿: ' + json.dumps(args, ensure_ascii=False)
                pending = calls[0]['id']
            after_result = False
        elif role == 'tool':
            if not pending or m.get('tool_call_id') != pending:
                raise ValueError('Unexpected tool result')
            prompt += '\n✿RESULT✿: ' + m['content'] + '\n✿RETURN✿'
            pending = None
            after_result = True
        else:
            raise ValueError('Unsupported history role')
    if pending:
        raise ValueError('Cannot generate before a real tool result')
    if not open_assistant:
        prompt += '\n<|im_start|>assistant\n'
    elif not after_result:
        raise ValueError('History must end in a user or resolved tool observation')
    return prompt


def split_boundary(text):
    """Return parser text and observed stop marker; preserve full text separately.

    A stop can finish inside a token that also contains a colon or whitespace.
    Any other generated tail is rejected rather than silently discarded.
    """
    hits = [(text.find(s), s) for s in STOPS if s in text]
    if not hits:
        return text, None
    index, marker = min(hits)
    tail = text[index + len(marker):]
    if tail.strip() not in ('', ':'):
        raise ValueError('Generated content after tool boundary')
    return text[:index], marker
