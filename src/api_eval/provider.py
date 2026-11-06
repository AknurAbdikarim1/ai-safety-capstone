"""Standard-library HTTPS client: exact bodies, chunk journaling, no retries."""
import http.client
import os
import time
from urllib.parse import urlsplit
from api_eval.records import decode, encode
from api_eval.evidence import utc

SAFE_HEADERS = {'content-type', 'date', 'x-request-id', 'request-id',
                'x-neurometric-request-id', 'x-taskrouter-model', 'x-taskrouter-reason',
                'x-taskrouter-task', 'retry-after', 'x-ratelimit-limit-tokens',
                'x-ratelimit-remaining-tokens', 'x-ratelimit-reset-tokens',
                'x-ratelimit-limit-requests', 'x-ratelimit-remaining-requests', 'x-ratelimit-reset-requests'}


class Provider:
    def __init__(self, config, evidence):
        self.config, self.evidence = config, evidence

    def invoke(self, request, number):
        cfg, ev = self.config, self.evidence
        prefix = f'raw/calls/{number:04d}/attempt_01'
        body = encode(request)
        key = os.environ.get(cfg['provider']['key_env'])
        if not key:
            raise ValueError('Configured API key environment variable is missing')
        if key.encode() in body:
            raise ValueError('Credential material found in request')
        ev.put(prefix + '/request.body.json', body)
        ev.put(prefix + '/request.meta.json', {'utc': utc(), 'endpoint': cfg['provider']['endpoint'],
            'attempt': 1, 'authentication': 'omitted', 'automatic_retries': 0})
        url = urlsplit(cfg['provider']['endpoint'])
        conn = http.client.HTTPSConnection(url.hostname, url.port,
                    timeout=cfg['limits']['request_timeout_seconds'])
        start = time.monotonic()
        chunks = []
        try:
            conn.request('POST', url.path, body, {'Content-Type': 'application/json',
                         'Authorization': 'Bearer ' + key, 'Accept-Encoding': 'identity'})
            response = conn.getresponse()
            safe_headers = {k.lower(): v for k, v in response.getheaders() if k.lower() in SAFE_HEADERS}
            if any(key in value for value in safe_headers.values()):
                raise ValueError('Credential material in response headers')
            ev.put(prefix + '/response.headers.json', {'status': response.status,
                'headers': safe_headers,
                'utc': utc()})
            # Nonstreaming HTTP; read body in durable chunks so interrupted exchanges retain bytes.
            total = 0
            while True:
                chunk = response.read1(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > 16 * 1024 * 1024:
                    raise ValueError('API response capture limit exceeded')
                if key.encode() in b''.join(chunks[-1:]) + chunk:
                    raise ValueError('Credential material in response; capture stopped')
                ev.put(prefix + f'/chunks/{len(chunks):06d}.bin', chunk)
                chunks.append(chunk)
                if time.monotonic() - start > cfg['limits']['request_timeout_seconds']:
                    raise TimeoutError('API wall-clock deadline exceeded')
            if getattr(response, 'length', None) not in (None, 0):
                raise ValueError('Incomplete HTTP response body')
            raw = b''.join(chunks)
            ev.put(prefix + '/response.body', raw)
            ev.put(prefix + '/response.meta.json', {'status': response.status,
                'latency_seconds': time.monotonic() - start, 'complete': True, 'utc': utc()})
            if response.status != 200:
                raise RuntimeError('HTTP request failed; see preserved response status/body')
            return decode(raw)
        except Exception as exc:
            # Never serialize SDK/request/exception objects that might include credentials.
            ev.put(prefix + '/error.json', {'type': type(exc).__name__,
                'received_chunks': len(chunks), 'latency_seconds': time.monotonic()-start,
                'charge_unknown': True, 'automatic_retry': False})
            raise RuntimeError('API exchange failed; inspect saved evidence') from None
        finally:
            conn.close()
