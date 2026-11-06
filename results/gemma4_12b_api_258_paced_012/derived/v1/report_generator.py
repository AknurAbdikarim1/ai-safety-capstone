"""Offline derived readability exports; raw evidence is never modified."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'src/api_eval').is_dir())
sys.path.insert(0,str(ROOT/'src'))
from api_eval.validate_run import validate


def read(path):
    return json.loads(path.read_text())


def fenced(value, language='text'):
    text=value if isinstance(value,str) else json.dumps(value,indent=2,ensure_ascii=False)
    fence='`'*max(3,1+max([len(x) for x in re.findall(r'`+',text)] or [0]))
    return fence+language+'\n'+text+'\n'+fence+'\n'


def generate(directory):
    root=Path(directory).resolve();raw=root/'raw'
    if not (raw/'terminal.json').is_file():raise ValueError('Wait until the run is finalized')
    output=root/'derived/v1';output.mkdir(parents=True,exist_ok=False,mode=0o700)
    terminal=read(raw/'terminal.json');config=read(raw/'config.resolved.json')
    transcript=['# Full autonomous rollout transcript\n',
        'Derived readability export. Exact per-call requests/responses and command bytes under raw/ remain authoritative. Call headings are added labels, not model text.\n',
        '## Original instructions\n',fenced(read(raw/'prompts.json'),'json')]
    thoughts=['DERIVED REASONING EXPORT\nCall/field headings are labels. Text below is copied from actual returned fields; missing reasoning is never generated. This file is not a reconstructed model/token input.\n']
    rows=[]; api_messages=[];total_in=total_out=0;known_cost=0.;reasoning_calls=0
    for call in sorted((raw/'calls').iterdir()):
        if not call.is_dir():continue
        number=int(call.name);structured=call/'structured.json'
        if not structured.exists():
            transcript.extend([f'## Call {number}: no structured assistant response\n'])
            error=call/'attempt_01/error.json'
            if error.exists():transcript.append(fenced(read(error),'json'))
            response=call/'attempt_01/response.body'
            if response.exists():transcript.append(fenced(response.read_text()))
            continue
        body=read(structured);choice=body['choices'][0];message=choice.get('message',{})
        usage=body.get('usage',{});inp=usage.get('prompt_tokens');out=usage.get('completion_tokens')
        if isinstance(inp,int) and isinstance(out,int):
            total_in+=inp;total_out+=out
            known_cost+=(inp*config['billing']['input_per_million']+out*config['billing']['output_per_million'])/1e6
        row={'call':number,'finish_reason':choice.get('finish_reason'),'usage':usage,'model':body.get('model'),
             'completion_id':body.get('id'),'reasoning_fields':[],'tool_calls':[]}
        transcript += [f'## Call {number}\n',f'Finish reason: `{choice.get("finish_reason")}`; reported usage: {json.dumps(usage)}.\n']
        api_messages.append({'call':number,'role':'assistant','message':message})
        for field in ('reasoning_content','reasoning','reasoning_details','reasoning_summary'):
            if message.get(field) not in (None,'',[]):
                row['reasoning_fields'].append(field)
                text=message[field] if isinstance(message[field],str) else json.dumps(message[field],ensure_ascii=False,indent=2)
                thoughts.extend([f'\n===== CALL {number:04d} | FIELD {field} | FINISH {choice.get("finish_reason")} =====\n',text,'\n'])
                transcript.extend([f'### Returned `{field}`\n',fenced(text)])
        if row['reasoning_fields']:reasoning_calls+=1
        else:transcript.append('No nonempty reasoning field returned for this call.\n')
        if message.get('content') not in (None,''):
            transcript.extend(['### Assistant content\n',fenced(message['content'])])
        for tool in message.get('tool_calls') or []:
            row['tool_calls'].append(tool)
            transcript.extend(['### Requested tool call\n',fenced(tool,'json')])
        action=raw/f'actions/{number:04d}/result.json'
        if action.exists():
            result=read(action);row['actual_exit_code']=result['return_code']
            transcript.extend(['### Actual Docker result delivered to the model\n',fenced(result['model_visible_content'])])
            api_messages.append({'call':number,'role':'tool','tool_call_id':read(action.parent/'intent.json')['provider_tool_call_id'],
                                 'content':result['model_visible_content'],'result_artifact':str(action.relative_to(root))})
        elif message.get('tool_calls'):
            transcript.append('No retained execution result. Do not infer execution or fabricate an observation.\n')
        rows.append(row)
    validation=validate(root)
    preflight=read(raw/'verification/preflight.json') if (raw/'verification/preflight.json').exists() else None
    submission=read(raw/'verification/submission.json') if (raw/'verification/submission.json').exists() else None
    summary={'run_directory':str(root),'terminal':terminal,'call_count':len(rows),
        'api_request_count':len(list((raw/'calls').glob('*/attempt_01/request.body.json'))),
        'model_command_results':len(list((raw/'actions').glob('*/result.json'))),'reasoning_calls':reasoning_calls,
        'total_reported_input_tokens':total_in,'total_reported_output_tokens':total_out,'estimated_known_usage_cost_usd':known_cost,
        'cost_excludes_unknown_charges_and_previous_campaign_reservations':True,'calls':rows,
        'evidence_validation':validation,'preflight_passed':preflight.get('passed') if preflight else None,
        'submission_mechanical_checks_passed':submission.get('mechanical_checks_passed') if submission else None,
        'interpretation':'Controller termination and mechanical checks are not automatic task-success, semantic-correctness or deception labels.'}
    for name,value in [('run_summary.json',summary),('evidence_validation.json',validation)]:
        with (output/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False)
    with (output/'full_transcript.md').open('x') as f:f.write('\n'.join(transcript))
    with (output/'all_reasoning.txt').open('x') as f:f.write(''.join(thoughts))
    with (output/'messages.jsonl').open('x') as f:
        for msg in api_messages:f.write(json.dumps(msg,ensure_ascii=False)+'\n')
    shutil.copyfile(__file__,output/'report_generator.py')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('calls','evidence_validation')},indent=2))


if __name__=='__main__':generate(sys.argv[1])
