"""Two-stage thinking/JSON generation with selected online activations and replay."""
import hashlib
import importlib.metadata
import json
import random
import time
from qwen_adapter.local_model import LocalQwen
from qwen_adapter import thinking_format as fmt


class ThinkingQwen(LocalQwen):
    supports_artifacts = True

    def __init__(self, model_id, settings):
        if model_id not in fmt.MODEL_REVISIONS or settings['revision'] != fmt.MODEL_REVISIONS[model_id]:
            raise ValueError('Use the pinned thinking condition')
        super().__init__(model_id, settings)
        from lmformatenforcer.integrations.transformers import build_token_enforcer_tokenizer_data
        if self.model.config.hidden_size != 2560 or self.tokenizer.encode('</think>', add_special_tokens=False) != [fmt.CLOSE_THINK]:
            raise ValueError('Unexpected model/tokenizer architecture')
        self.enforcer_data = build_token_enforcer_tokenizer_data(self.tokenizer)
        self.metadata['native_thinking_flag'] = True if model_id == fmt.HYBRID_MODEL else 'dedicated_thinking_checkpoint'
        self.metadata.update(schema_sha256=hashlib.sha256(json.dumps(fmt.SCHEMA, sort_keys=True).encode()).hexdigest(),
            lm_format_enforcer=importlib.metadata.version('lm-format-enforcer'),
            activation_location='decoder block output, one-based layer numbering, CPU float32',
            activation_positions={'P0': 'last input token before native thinking generation',
                                 'R1': 'last harness-inserted tool prefix token after natural thinking; before JSON choice'},
            memory_instrumentation='stage_boundaries_v1',
            adaptation='Native template plus final_report tool, injected tool prefix and constrained JSON; not unmodified native tool evaluation')

    def _hooks(self, destination):
        handles = []
        for layer in self.settings['activation_layers']:
            def capture(module, args, output, key=str(layer)):
                if key not in destination:
                    value = output[0] if isinstance(output, tuple) else output
                    destination[key] = value[0, -1].detach().float().cpu().clone()
            handles.append(self.model.model.layers[layer-1].register_forward_hook(capture))
        return handles

    def _memory_snapshot(self, stage, event, input_tokens):
        """CPU-only scalar telemetry; never retain GPU tensors or clear caches."""
        cuda = self.torch.cuda
        record = {'stage': stage, 'event': event, 'input_tokens': input_tokens,
                  'cuda_available': cuda.is_available()}
        if record['cuda_available']:
            device = self.model.device
            free, total = cuda.mem_get_info(device)
            record.update(device=str(device), free_bytes=free, total_bytes=total,
                allocated_bytes=cuda.memory_allocated(device),
                reserved_bytes=cuda.memory_reserved(device),
                call_peak_allocated_bytes=cuda.max_memory_allocated(device),
                call_peak_reserved_bytes=cuda.max_memory_reserved(device))
        return record

    def _run_stage(self, ids, maximum, eos, capture, **extra):
        torch = self.torch
        handles = self._hooks(capture)
        try:
            inputs = torch.tensor([ids], device=self.model.device, dtype=torch.long)
            with torch.inference_mode():
                output = self.model.generate(input_ids=inputs, attention_mask=torch.ones_like(inputs),
                    max_new_tokens=maximum, do_sample=True,
                    temperature=self.settings['temperature'], top_p=self.settings['top_p'],
                    top_k=self.settings['top_k'], repetition_penalty=1.0,
                    eos_token_id=eos, pad_token_id=151643, use_cache=True, **extra)
            return output[0, len(ids):].tolist()
        finally:
            for handle in handles: handle.remove()

    def _replay(self, ids, online):
        torch = self.torch
        replay = {}
        handles = self._hooks(replay)
        try:
            inputs = torch.tensor([ids], device=self.model.device, dtype=torch.long)
            with torch.inference_mode():
                self.model.model(input_ids=inputs, attention_mask=torch.ones_like(inputs),
                                 use_cache=False, output_hidden_states=False, return_dict=True)
        finally:
            for handle in handles: handle.remove()
        differences = {key: (online[key]-replay[key]).abs().max().item() for key in online}
        passed = all(torch.allclose(online[key], replay[key], atol=0.01, rtol=0.01) for key in online)
        return {'prefix_token_ids': ids, 'token_index': len(ids)-1,
                'vectors': {key: value.tolist() for key, value in online.items()},
                'replay_max_abs_difference': differences, 'replay_atol': 0.01, 'replay_rtol': 0.01,
                'replay_passed': passed}

    def generate(self, request, on_input=None, on_artifact=None):
        from lmformatenforcer import JsonSchemaParser
        from lmformatenforcer.integrations.transformers import build_transformers_prefix_allowed_tokens_fn
        torch = self.torch
        random.seed(self.settings['seed'])
        import numpy as np
        np.random.seed(self.settings['seed'])
        torch.manual_seed(self.settings['seed'])
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.settings['seed'])
            torch.cuda.reset_peak_memory_stats()
        started = time.monotonic()
        rendered = fmt.render(self.tokenizer, request)
        ids = self.tokenizer.encode(rendered, add_special_tokens=False)
        injected = self.tokenizer.encode(fmt.JSON_PREFIX, add_special_tokens=False)
        reserve = self.settings['thinking_max_new_tokens'] + len(injected) + self.settings['max_new_tokens']
        if on_input:
            on_input({'input_token_ids': ids, 'rendered_prompt': rendered, 'settings': self.settings,
                      'model_metadata': self.metadata, 'prefix_last_token_index': len(ids)-1})
        if len(ids) + reserve > self.settings['max_context_tokens']:
            raise ValueError('Context budget exceeded; no history truncated')
        raw = {'input_token_ids': ids, 'generated_token_ids': [], 'phases': {}, 'activations': {},
               'injected_prefix_text': fmt.JSON_PREFIX, 'injected_prefix_token_ids': injected,
               'text': '', 'raw_decoded_text': '', 'tool_interface': fmt.INTERFACE,
               'stop_reason': 'incomplete', 'model_metadata': self.metadata, 'memory_records': [],
               'seed_policy': 'reset_configured_seed_per_call; same RNG stream across stages'}
        def save(tag, record):
            if on_artifact: on_artifact(tag, record)
        def measured(stage, prefix, operation):
            raw['memory_records'].append(self._memory_snapshot(stage, 'before', len(prefix)))
            save('memory_' + stage + '_before', raw['memory_records'][-1])
            try:
                result = operation()
            except Exception:
                # Preserve the original generation error even if post-OOM telemetry fails.
                try:
                    raw['memory_records'].append(self._memory_snapshot(stage, 'error', len(prefix)))
                    save('memory_' + stage + '_error', raw['memory_records'][-1])
                except Exception:
                    pass
                raise
            raw['memory_records'].append(self._memory_snapshot(stage, 'after', len(prefix)))
            save('memory_' + stage + '_after', raw['memory_records'][-1])
            return result
        try:
            online0 = {}
            thinking = measured('thinking', ids, lambda: self._run_stage(ids, self.settings['thinking_max_new_tokens'], [fmt.CLOSE_THINK, 151645, 151643], online0))
            phase = {'input_token_ids': ids, 'generated_token_ids': thinking,
                     'text': self.tokenizer.decode(thinking, skip_special_tokens=False, clean_up_tokenization_spaces=False)}
            raw['phases']['thinking'] = phase
            raw['generated_token_ids'] = thinking
            raw['text'] = raw['raw_decoded_text'] = phase['text']
            save('thinking', phase)
            raw['P0_online'] = {key: value.tolist() for key,value in online0.items()}
            save('P0_online', {'prefix_token_ids': ids, 'vectors': raw['P0_online']})
            if thinking[-1:] != [fmt.CLOSE_THINK]:
                return raw
            continuation = ids + thinking + injected
            online1 = {}
            enforcer = build_transformers_prefix_allowed_tokens_fn(self.enforcer_data, JsonSchemaParser(fmt.SCHEMA))
            action = measured('action', continuation, lambda: self._run_stage(continuation, self.settings['max_new_tokens'], [151645], online1,
                                     prefix_allowed_tokens_fn=enforcer))
            body = self.tokenizer.decode(action[:-1] if action[-1:] == [151645] else action,
                                         skip_special_tokens=False, clean_up_tokenization_spaces=False)
            raw['phases']['action'] = {'input_token_ids': continuation, 'generated_token_ids': action, 'text': body}
            raw['generated_token_ids'] = thinking + action
            raw['text'] = raw['raw_decoded_text'] = phase['text'] + fmt.JSON_PREFIX + body
            save('action', raw['phases']['action'])
            raw['R1_online'] = {key: value.tolist() for key,value in online1.items()}
            save('R1_online', {'prefix_token_ids': continuation, 'vectors': raw['R1_online']})
            if action[-1:] != [151645]: return raw
            # Validate content before spending extra passes on exact-prefix replay.
            fmt.parse(raw['text'])
            for name, prefix, online in [('P0', ids, online0), ('R1', continuation, online1)]:
                raw['activations'][name] = measured('replay_' + name, prefix, lambda: self._replay(prefix, online))
                save(name, raw['activations'][name])
            raw['stop_reason'] = 'eos'
        except Exception as exc:
            raw['generation_error'] = f'{type(exc).__name__}: {exc}'
            raw['stop_reason'] = 'error'
        finally:
            raw['elapsed_seconds'] = time.monotonic()-started
            if torch.cuda.is_available():
                raw['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
                raw['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
        return raw
