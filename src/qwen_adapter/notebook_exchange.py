"""Manual notebook transport: encode request data as a safely quoted Python literal."""
import json
from qwen_adapter.manual_exchange import validate_request


def request_cell(request):
    validate_request(request)
    # repr produces a Python string literal; JSON is never interpolated as executable code.
    encoded = repr(json.dumps(request, ensure_ascii=False))
    return ('import json\nrequest = json.loads(' + encoded + ')\n'
            'bundle, parsed = evaluate_and_save(request)\n'
            'print("Import this call bundle on Mac:", request["call_id"])\n')
