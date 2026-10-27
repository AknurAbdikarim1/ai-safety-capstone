"""Upload this file to the existing Colab session; no commands are executed.

Call run_calibration(engine, '/content/NEW_CALIBRATION_DIR') using the already
loaded LocalQwen engine. Tool results below are explicitly simulated fixtures.
"""
import json
from pathlib import Path
import uuid

from qwen_adapter.protocol import canonical_message, parse_output


REMINDER = ('Return at most one tool call per turn. Enclose its JSON in '
            '<tool_call> and </tool_call>, then wait for the tool result.')
TOOL = {'type': 'function', 'function': {
    'name': 'execute_command',
    'description': 'Execute a shell command in the UNIX environment. Returns the command output and exit code.',
    'parameters': {'type': 'object', 'properties': {'command': {
        'type': 'string', 'description': 'The shell command to execute'}}, 'required': ['command']}}}


def run_calibration(engine, output_dir):
    """Compare two neutral formatting conditions, at most four generations total."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    summary = {'purpose': 'tool-format calibration, not behavioral research data',
               'shell_execution': False, 'tool_results': 'simulated', 'conditions': {}}
    for condition, extra in [('baseline', ''), ('format_reminder', '\n' + REMINDER)]:
        messages = [
            {'role': 'system', 'content': 'You are an assistant with access to an execute_command tool. Execute one command per turn.' + extra},
            {'role': 'user', 'content': 'Call execute_command exactly once with the command printf CALIBRATION_OK. Wait for its tool result before answering.'},
        ]
        result = {'passed': False, 'generations': 0}
        summary['conditions'][condition] = result
        for turn in [1, 2]:
            prefix = f'{condition}_turn_{turn}'
            request = {'call_id': uuid.uuid4().hex, 'model': engine.model_id,
                       'settings': engine.settings, 'messages': messages, 'tools': [TOOL]}
            (output / f'{prefix}.request.json').write_text(json.dumps(request, indent=2))
            try:
                raw = engine.generate(request, on_input=lambda value: (
                    output / f'{prefix}.input.json').write_text(json.dumps(value)))
                result['generations'] += 1
                (output / f'{prefix}.generation.json').write_text(json.dumps(raw, indent=2))
                if raw['stop_reason'] != 'eos':
                    raise ValueError('incomplete generation')
                parsed = parse_output(raw['text'])
                (output / f'{prefix}.parsed.json').write_text(json.dumps(parsed, indent=2))
                if turn == 1:
                    if parsed['kind'] != 'tool' or parsed['command'] != 'printf CALIBRATION_OK':
                        raise ValueError('expected one exact calibration command')
                    messages.append(canonical_message(parsed, request['call_id']))
                    fixture = {'role': 'tool', 'tool_call_id': request['call_id'],
                               'name': 'execute_command', 'content': 'Exit code: 0\nCALIBRATION_OK'}
                    (output / f'{prefix}.simulated_tool_result.json').write_text(json.dumps(fixture, indent=2))
                    messages.append(fixture)
                    messages.append({'role': 'user', 'content': 'Now report the tool output in one short sentence. Do not call tools.'})
                elif parsed['kind'] != 'report' or 'CALIBRATION_OK' not in parsed['report']:
                    raise ValueError('expected a text report containing the fixture output')
                else:
                    result['passed'] = True
            except Exception as exc:
                result['error'] = f'{type(exc).__name__}: {exc}'
                break
        (output / 'summary.json').write_text(json.dumps(summary, indent=2))
    return summary
