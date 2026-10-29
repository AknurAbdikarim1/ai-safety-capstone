"""Qwen generation. Heavy libraries import only when constructing the worker."""
import copy
import hashlib
import json
import importlib.metadata
import platform
import random
import time


class LocalQwen:
    def __init__(self, model_id, settings):
        import torch
        from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.model_id, self.settings = model_id, settings
        device = settings['device']
        if device == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable; choose the actual GPU runtime')
        dtype = {'float16': torch.float16, 'float32': torch.float32}[settings['dtype']]
        config = AutoConfig.from_pretrained(model_id, revision=settings['revision'])
        resolved = getattr(config, '_commit_hash', None) or settings['revision']
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=resolved)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id, revision=resolved, config=config, torch_dtype=dtype,
            device_map={'': device}, attn_implementation='sdpa').eval()
        self.metadata = {
            'model': model_id, 'requested_revision': settings['revision'],
            'resolved_revision': getattr(self.model.config, '_commit_hash', None),
            'template_sha256': hashlib.sha256(self.tokenizer.chat_template.encode()).hexdigest(),
            'tool_history_format': 'object_arguments_v1',
            'versions': {n: importlib.metadata.version(n) for n in ['torch', 'transformers', 'numpy', 'accelerate']},
            'python': platform.python_version(), 'device': device, 'dtype': settings['dtype'],
            'gpu': torch.cuda.get_device_name(0) if device == 'cuda' else None,
            'attention_implementation': 'sdpa', 'hidden_size': self.model.config.hidden_size}

        self.metadata['tool_interface'] = settings.get('tool_interface', 'xml_single_v1')
        if self.metadata['tool_interface'] == 'qwen_serial_v1':
            from pathlib import Path
            from qwen_adapter import serial_format
            self.metadata['serial_format_sha256'] = hashlib.sha256(
                Path(serial_format.__file__).read_bytes()).hexdigest()
        self.metadata['resolved_generation_config'] = self.model.generation_config.to_dict()

    def generate(self, request, on_input=None):
        torch = self.torch
        seed = self.settings['seed']  # fixed per-call seed; recorded explicitly, not independent task replication
        random.seed(seed)
        import numpy as np
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        # The controller uses OpenAI-style JSON strings, whereas Qwen's template
        # applies tojson itself. Decode only the history representation, never
        # model output, and leave the hashed request unchanged.
        messages = copy.deepcopy(request['messages'])
        for message in messages:
            for call in message.get('tool_calls', []):
                function = call['function']
                arguments = function['arguments']
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                if not isinstance(arguments, dict):
                    raise ValueError('Tool history arguments must be a JSON object')
                function['arguments'] = arguments
        interface = self.settings.get('tool_interface', 'xml_single_v1')
        rendered = None
        if interface == 'qwen_serial_v1':
            from qwen_adapter.serial_format import render_prompt
            rendered = render_prompt(messages, request['tools'])
            inputs = self.tokenizer(rendered, add_special_tokens=False, return_tensors='pt').to(self.settings['device'])
        elif interface == 'xml_single_v1':
            inputs = self.tokenizer.apply_chat_template(
                messages, tools=request['tools'], add_generation_prompt=True,
                tokenize=True, return_dict=True, return_tensors='pt').to(self.settings['device'])
        else:
            raise ValueError('Unknown tool interface')
        ids = inputs['input_ids'][0].tolist()
        if on_input is not None:
            on_input({'input_token_ids': ids, 'model_metadata': self.metadata,
                      'settings': self.settings, 'rendered_prompt': rendered,
                      'tool_interface': interface, 'prefix_last_token_index': len(ids) - 1})
        budget = min(self.settings['max_context_tokens'], self.model.config.max_position_embeddings)
        if len(ids) + self.settings['max_new_tokens'] > budget:
            raise ValueError('Context budget exceeded; no input was silently truncated')
        kw = {'max_new_tokens': self.settings['max_new_tokens'],
              'do_sample': self.settings['do_sample'], 'pad_token_id': self.tokenizer.eos_token_id}
        if self.settings['do_sample']:
            kw.update(temperature=self.settings['temperature'], top_p=self.settings['top_p'])
        if interface == 'qwen_serial_v1':
            from qwen_adapter.serial_format import STOPS
            kw.update(stop_strings=list(STOPS), tokenizer=self.tokenizer)
        started = time.monotonic()
        with torch.inference_mode():
            output = self.model.generate(**inputs, **kw)
        generated = output[0, len(ids):].tolist()
        eos = self.model.generation_config.eos_token_id
        eos = eos if isinstance(eos, list) else [eos]
        stopped = bool(generated and generated[-1] in eos)
        # Decode explicitly after removing only terminal EOS; retain tool markup and other tokens.
        payload = generated[:-1] if stopped else generated
        text = self.tokenizer.decode(payload, skip_special_tokens=False)
        raw_decoded_text = text
        marker = None
        boundary_error = None
        if interface == 'qwen_serial_v1':
            from qwen_adapter.serial_format import split_boundary
            try:
                text, marker = split_boundary(text)
            except ValueError as exc:
                boundary_error = str(exc)
        reason = ('invalid_boundary' if boundary_error else
                  'tool_boundary' if marker else 'eos' if stopped else 'incomplete')
        return {'text': text, 'raw_decoded_text': raw_decoded_text,
                'stop_marker': marker, 'boundary_error': boundary_error,
                'tool_interface': interface, 'input_token_ids': ids, 'generated_token_ids': generated,
                'stop_reason': reason, 'seed_policy': 'reset_configured_seed_per_call',
                'elapsed_seconds': time.monotonic() - started, 'model_metadata': self.metadata}
