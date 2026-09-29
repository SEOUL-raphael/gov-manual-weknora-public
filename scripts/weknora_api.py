"""Small v0.8.0 API client. No credentials or raw error responses are logged."""
import os
from pathlib import Path
import httpx
import truststore
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
if not Path(os.environ.get('SSL_CERT_FILE','')).is_file():
    os.environ.pop('SSL_CERT_FILE', None)
truststore.inject_into_ssl()

class ApiError(RuntimeError):
    pass

class API:
    def __init__(self, config=None, client=None):
        self.config = config or dotenv_values(ROOT/'.env')
        port = self.config.get('API_PORT','18766')
        self.client = client or httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=120,
                                            headers={'Accept-Language':'ko-KR'}, trust_env=False)

    def call(self, method, path, **kwargs):
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.TransportError as exc:
            raise ApiError(f'{method} {path}: {type(exc).__name__}; no automatic write retry') from None
        if not response.is_success:
            raise ApiError(f'{method} {path}: HTTP {response.status_code}')
        data = response.json()
        if data.get('success') is False:
            raise ApiError(f'{method} {path}: success=false')
        return data

    def login(self):
        data = self.call('POST','/api/v1/auth/login',json={
            'email':self.config['ADMIN_EMAIL'], 'password':self.config['ADMIN_PASSWORD']})
        self.client.headers['Authorization'] = 'Bearer '+data['token']

    def close(self):
        self.client.close()
