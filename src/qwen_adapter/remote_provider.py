"""Upstream BaseProvider implementation; inference executes in the notebook."""
import copy
import json
from pathlib import Path
import uuid

from agent_interp_envs.providers.base import BaseProvider
from agent_interp_envs.types import LLMResponse, ToolCall
from qwen_adapter.protocol import canonical_message, parse_output
from qwen_adapter.spool import digest, wait_response, write_new


class QwenRemoteProvider(BaseProvider):
    strict_tool_protocol = True

    def __init__(self, model, messages, tools, qwen_options):
        self.model = model
        self.messages = copy.deepcopy(messages)
        self.tools = tools
        self.options = qwen_options
        self.directory = Path(qwen_options['bridge_dir'])
        if messages and messages[-1].get('role') == 'assistant' and messages[-1].get('tool_calls'):
            raise ValueError('History ends in an unresolved action; manual recovery required')
        self.pending = None
        self.last_call_id = None
        self.settings = qwen_options['generation']
        if model != 'Qwen/Qwen2.5-3B-Instruct':
            raise ValueError('This integration is validated only for the configured Qwen model')
        if len(tools) != 1 or tools[0]['function']['name'] != 'execute_command':
            raise ValueError('Only the original single execute_command tool is supported')

    def invoke(self):
        if self.pending:
            raise RuntimeError('Previous tool result is missing')
        call_id = uuid.uuid4().hex
        self.last_call_id = call_id
        request = {'call_id': call_id, 'model': self.model, 'settings': self.settings,
                   'messages': self.messages, 'tools': self.tools}
        request['request_hash'] = digest(request)
        write_new(self.directory / f'{call_id}.request.json', request)
        response = wait_response(self.directory, call_id, self.options['timeout_seconds'])
        if response.get('request_hash') != request['request_hash']:
            raise RuntimeError('Response does not match request')
        if response.get('error'):
            raise RuntimeError('Inference/protocol failure: ' + response['error'])
        # Parse independently at both trust boundaries. Never execute worker-supplied code.
        parsed = parse_output(response['text'], self.settings.get('tool_interface', 'xml_single_v1'))
        if parsed != response['parsed']:
            raise RuntimeError('Worker/controller parser mismatch')
        self.messages.append(canonical_message(parsed, call_id))
        if parsed['kind'] == 'tool':
            self.pending = call_id
            return LLMResponse(parsed['working_text'], None, [ToolCall(
                id=call_id, name='execute_command', arguments=json.dumps({'command': parsed['command']}))])
        return LLMResponse(None, parsed['report'], None)

    def add_tool_result(self, tool_result):
        if tool_result.id != self.pending:
            raise RuntimeError('Unexpected or repeated tool result')
        self.messages.append({'role': 'tool', 'tool_call_id': tool_result.id,
                              'name': tool_result.name, 'content': tool_result.content})
        write_new(self.directory / f'{self.pending}.tool_result.json', {
            'call_id': self.pending, 'name': tool_result.name, 'content': tool_result.content})
        self.pending = None

    def revert_last_turn(self):
        # No transparent retries: a prior tool may have already changed the workspace.
        raise RuntimeError('Automatic turn reversal is disabled for experimental runs')

    def print_history(self):
        print(self.dump_history())
