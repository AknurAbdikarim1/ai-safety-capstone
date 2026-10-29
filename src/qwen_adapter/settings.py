"""Fail early on unsupported protocol/configuration instead of changing it silently."""


def validate(config):
    if config.get('environment') != 'precommit_hook':
        raise ValueError('Expected Pre-commit Hook')
    agent = config['agent']
    if agent['provider'] != 'qwen_local' or agent['model'] != 'Qwen/Qwen2.5-3B-Instruct':
        raise ValueError('Expected Qwen2.5-3B-Instruct local integration')
    if config['protocol']['reasoning'] != 'spontaneous_working_text_only':
        raise ValueError('Only original-prompt mode is implemented; elicitation needs protocol review')
    if config['task'].get('tools') != ['execute_command']:
        raise ValueError('Expected the original single tool')
    if any(config['task'].get(k, False) for k in ['memory_tools', 'plan_tools', 'question_tool', 'done_tool']):
        raise ValueError('Optional tools are outside the initial integration')
    if not isinstance(agent['max_steps'], int) or agent['max_steps'] < 1:
        raise ValueError('max_steps must be positive')
    options = agent['qwen_options']
    if options['timeout_seconds'] <= 0:
        raise ValueError('Worker timeout must be positive')
    settings = options['generation']
    if settings.get('tool_interface', 'xml_single_v1') not in ('xml_single_v1', 'qwen_serial_v1'):
        raise ValueError('Unknown tool interface')
    if settings['device'] not in ['cuda', 'cpu'] or settings['dtype'] not in ['float16', 'float32']:
        raise ValueError('Unsupported device/dtype')
    if settings['device'] == 'cpu' and settings['dtype'] != 'float32':
        raise ValueError('Use float32 for CPU debugging')
    if not settings['revision'] or settings['max_new_tokens'] < 1 or settings['max_context_tokens'] <= settings['max_new_tokens']:
        raise ValueError('Invalid revision or token budget')
    if not isinstance(settings['seed'], int) or not 0 <= settings['seed'] < 2**32:
        raise ValueError('seed must be an unsigned 32-bit integer')
    if not isinstance(settings['do_sample'], bool):
        raise ValueError('do_sample must be boolean')
    if settings['temperature'] <= 0 or not 0 < settings['top_p'] <= 1:
        raise ValueError('Invalid sampling settings')
    return config
