"""Regressions use synthetic credentials and mocked provider transport only."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import socket
import httpx
import pytest
from sqlalchemy import select, update
from app.ai.providers import HTTPProvider, OpenAIProvider, GeminiProvider, provider_error
from app.ai.endpoints import PublicEndpointTransport, validate_endpoint
from app.services.exceptions import LLMRequestError, StorageUnavailableError
from app.services import llm, report_storage
from app.core.config import Settings
from app.db.models import WorkspaceLLMConfiguration
from tests.backend.test_guest_workspaces import setup, OPENAI, GEMINI
from sqlalchemy.orm import Session


def test_multiple_entries_session_activation_expiry_isolation(setup):
    engine, left, right, calls = setup
    one = left.put('/api/v1/llm/config', json=OPENAI).json()['data']
    two = left.put('/api/v1/llm/config', json=GEMINI).json()['data']
    assert one['id'] != two['id']
    entries = left.get('/api/v1/llm/configs').json()['data']
    assert len(entries) == 2 and all(e['configured'] for e in entries)
    assert left.get('/api/v1/llm/config').json()['data']['id'] == one['id']
    assert right.post(f"/api/v1/llm/configs/{two['id']}/activate").status_code == 409
    assert left.post(f"/api/v1/llm/configs/{two['id']}/activate").json()['data']['id'] == two['id']
    assert left.post('/api/v1/llm/test', json={**GEMINI, 'id': two['id'], 'api_key': None}).status_code == 200
    # Saving a remembered entry must not clear the shared session cookie.
    left.put('/api/v1/llm/config', json={**OPENAI, 'remember': True})
    assert all(e['configured'] for e in left.get('/api/v1/llm/configs').json()['data'])
    with Session(engine) as db:
        db.execute(update(WorkspaceLLMConfiguration).where(WorkspaceLLMConfiguration.id == two['id']).values(expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)))
        db.commit()
    assert not left.get('/api/v1/llm/config').json()['data']['configured']
    left.delete('/api/v1/llm/config', params={'id': two['id']})
    assert not left.get('/api/v1/llm/config').json()['data']['configured']


def test_storage_failure_is_subsystem_only(setup, monkeypatch):
    _, left, _, _ = setup
    settings = Settings(_env_file=None, storage_provider='s3')
    assert 'STORAGE_BUCKET' in settings.storage_issues()[0]
    monkeypatch.setattr(report_storage, 'get_settings', lambda: settings)
    with pytest.raises(StorageUnavailableError):
        report_storage.S3ReportStorage()
    assert left.get('/api/v1/llm/providers').status_code == 200
    assert left.post('/api/v1/workspace').status_code == 204


@pytest.mark.parametrize('provider', ['openrouter', 'groq', 'anthropic', 'custom'])
def test_http_adapters_discover_test_generate(provider, monkeypatch):
    calls = []
    def request(self, method, path, **kwargs):
        calls.append((method, path, kwargs))
        if method == 'GET': return {'data': [{'id': 'vendor/model:v1'}, {'id': 'whisper-large'}]}
        if path == '/messages': return {'content': [{'type': 'text', 'text': 'OK'}]}
        return {'choices': [{'message': {'content': 'OK'}}]}
    monkeypatch.setattr(HTTPProvider, 'request', request)
    adapter = HTTPProvider('vendor/model:v1', 'synthetic-key', provider=provider, base_url='https://example.com/v1')
    assert adapter.discover_models() == ['vendor/model:v1']
    adapter.test_connection()
    assert adapter.generate_content(system_prompt='system', user_prompt='synthetic') == 'OK'
    assert calls[-1][2]['json']['model'] == 'vendor/model:v1'
    assert calls[-1][1] == ('/messages' if provider == 'anthropic' else '/chat/completions')


@pytest.mark.parametrize('status,code', [(401,'llm_invalid_key'),(403,'llm_invalid_key'),(404,'llm_model_unavailable'),(402,'llm_quota'),(429,'llm_rate_limited'),(504,'llm_timeout'),(500,'llm_unavailable')])
def test_safe_http_failures(status, code):
    response = httpx.Response(status, request=httpx.Request('GET','https://example.com'), text='secret')
    error = provider_error(httpx.HTTPStatusError('secret', request=response.request, response=response))
    assert error.code == code and 'secret' not in str(error)


@pytest.mark.parametrize('endpoint', ['http://example.com','https://key@example.com','https://example.com/?key=x','https://example.com:8443','https://example.com/#secret'])
def test_endpoint_validation(endpoint):
    with pytest.raises(LLMRequestError): validate_endpoint(endpoint)


@pytest.mark.parametrize('ip', ['127.0.0.1','10.0.0.1','169.254.169.254','::1','fc00::1','::ffff:127.0.0.1','100.100.100.200','168.63.129.16','64:ff9b::a9fe:a9fe','2002:7f00:1::'])
def test_private_dns_blocked(ip, monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: [(2,1,6,'',(ip,443))])
    with PublicEndpointTransport() as transport:
        with pytest.raises(LLMRequestError): transport.handle_request(httpx.Request('GET','https://example.com/models'))


def test_dns_is_pinned_and_tls_identity_preserved(monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: [(2,1,6,'',('8.8.8.8',443))])
    def send(self, request):
        assert request.url.host == '8.8.8.8'
        assert request.headers['Host'] == 'example.com'
        assert request.extensions['sni_hostname'] == 'example.com'
        return httpx.Response(200)
    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', send)
    with PublicEndpointTransport() as transport:
        transport.handle_request(httpx.Request('GET','https://example.com/models'))


def test_custom_never_reuses_other_origin_key(setup):
    _, left, _, _ = setup
    saved = left.put('/api/v1/llm/config', json=OPENAI).json()['data']
    response = left.post('/api/v1/llm/test', json={'id': saved['id'], 'provider':'custom','base_url':'https://example.com/v1','model':'vendor/model:v1'})
    assert response.json()['error'] == 'llm_key_required'


def test_sdk_discovery():
    openai = OpenAIProvider('gpt-4.1-mini','key',client=SimpleNamespace(models=SimpleNamespace(list=lambda **kwargs: [SimpleNamespace(id='gpt-4.1-mini'),SimpleNamespace(id='gpt-image-1')])) )
    assert openai.discover_models() == ['gpt-4.1-mini']
    gemini = GeminiProvider('gemini','key',client=SimpleNamespace(models=SimpleNamespace(list=lambda: [SimpleNamespace(name='models/gemini',supported_actions=['generateContent']),SimpleNamespace(name='models/embed',supported_actions=['embedContent'])])))
    assert gemini.discover_models() == ['gemini']


def test_migration_preserves_ciphertext_and_active_selection(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    from cryptography.fernet import Fernet
    encryption_key = Fernet.generate_key()
    ciphertext = Fernet(encryption_key).encrypt(llm._binding('a'*32, 'openai', 'gpt-4.1-mini') + b'legacy-key').decode()
    monkeypatch.setattr(llm, 'get_settings', lambda: SimpleNamespace(llm_encryption_key=encryption_key.decode()))
    url = 'sqlite:///' + (tmp_path / 'migration.db').as_posix()
    config = Config(str(root / 'backend/alembic.ini'))
    config.attributes['database_url'] = url
    config.attributes['configure_logger'] = False
    command.upgrade(config, '20261112_0002')
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO guest_workspaces (id, credential_hash, expires_at) VALUES (:id, :hash, '2030-01-01')"), {'id':'a'*32,'hash':'b'*64})
        db.execute(text("INSERT INTO workspace_llm_configurations (workspace_id,provider,model,encrypted_api_key,session_hash,expires_at) VALUES (:id,'openai','gpt-4.1-mini',:ciphertext,:hash,'2030-01-01')"), {'id':'a'*32,'hash':'c'*64,'ciphertext':ciphertext})
    command.upgrade(config, 'head')
    with engine.connect() as db:
        row = db.execute(text('SELECT * FROM workspace_llm_configurations')).mappings().one()
        assert row['active'] and row['id'] == row['workspace_id'] == 'a'*32
        assert row['encrypted_api_key'] == ciphertext and row['session_hash'] == 'c'*64
        assert row['base_url'] is None
    with Session(engine) as db:
        assert llm._decrypt(db.get(WorkspaceLLMConfiguration, 'a'*32)) == 'legacy-key'
    engine.dispose()


def test_sdk_test_and_generation_contracts():
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_text='OK')
    adapter = OpenAIProvider('gpt-4.1-mini','synthetic-key',client=SimpleNamespace(responses=SimpleNamespace(create=create)))
    adapter.test_connection()
    assert adapter.generate_content(system_prompt='system',user_prompt='synthetic') == 'OK'
    assert all(call['store'] is False for call in calls)
    assert 'temperature' not in calls[-1]
    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text='OK')
    adapter = GeminiProvider('gemini','synthetic-key',client=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    adapter.test_connection()
    assert adapter.generate_content(system_prompt='system',user_prompt='synthetic') == 'OK'


def test_redirects_are_not_followed_or_forwarded(monkeypatch):
    calls = []
    class Client:
        def __init__(self, **kwargs):
            assert kwargs['follow_redirects'] is False and kwargs['trust_env'] is False
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def request(self, method, url, **kwargs):
            calls.append(url)
            return httpx.Response(302, headers={'Location':'http://169.254.169.254'}, request=httpx.Request(method,url))
    monkeypatch.setattr(httpx, 'Client', Client)
    provider = HTTPProvider('model','key',provider='custom',base_url='https://example.com/v1')
    with pytest.raises(httpx.HTTPStatusError): provider.discover_models()
    assert calls == ['https://example.com/v1/models']


def test_storage_upload_fails_without_persistence(setup, monkeypatch):
    from app.services import medical_report
    from tests.backend.test_guest_workspaces import PATIENT
    from app.db.models import MedicalReport
    engine, left, _, _ = setup
    settings = Settings(_env_file=None, storage_provider='s3')
    monkeypatch.setattr(medical_report, 'settings', settings)
    monkeypatch.setattr(report_storage, 'get_settings', lambda: settings)
    report_storage.get_s3_report_storage.cache_clear()
    patient = left.post('/api/v1/patients', json=PATIENT).json()['data']['id']
    result = left.post(f'/api/v1/patients/{patient}/reports', files={'file':('synthetic.txt', b'synthetic text', 'text/plain')})
    assert result.status_code == 503 and 'not configured' in result.json()['message']
    with Session(engine) as db:
        assert db.scalars(select(MedicalReport)).all() == []

@pytest.mark.parametrize('provider', ['openai','gemini','openrouter','anthropic','groq','custom'])
def test_selected_provider_reaches_clinical_pipeline(setup, provider, monkeypatch):
    from tests.backend.test_guest_workspaces import PATIENT, CLINICAL, OUTPUT
    import json
    _, left, _, _ = setup
    calls = []
    def build(name, model, key, **kwargs):
        calls.append((name, model, key, kwargs))
        return SimpleNamespace(test_connection=lambda: None, generate_content=lambda **prompts: json.dumps(OUTPUT))
    monkeypatch.setattr(llm, 'build_ai_provider', build)
    payload = {'provider': provider, 'model':'vendor/model:v1','api_key':'synthetic-key'}
    if provider == 'custom': payload['base_url'] = 'https://example.com/v1'
    assert left.put('/api/v1/llm/config', json=payload).status_code == 200
    patient = left.post('/api/v1/patients', json=PATIENT).json()['data']['id']
    left.post(f'/api/v1/patients/{patient}/symptoms', json=CLINICAL['symptoms'])
    result = left.post(f'/api/v1/patients/{patient}/analyze')
    assert result.status_code == 200
    assert calls[-1][:3] == (provider, 'vendor/model:v1', 'synthetic-key')
    if provider == 'custom': assert calls[-1][3]['base_url'] == payload['base_url']

@pytest.mark.parametrize('provider', ['openrouter','groq','anthropic','custom'])
def test_http_authentication_uses_only_supplied_key(provider, monkeypatch):
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def request(self, method, url, **kwargs):
            headers = kwargs['headers']
            if provider == 'anthropic':
                assert headers == {'x-api-key':'synthetic-own-key', 'anthropic-version':'2026-10-21'}
            else:
                assert headers == {'Authorization':'Bearer synthetic-own-key'}
            return httpx.Response(200, json={'data':[]}, request=httpx.Request(method,url))
    monkeypatch.setattr(httpx, 'Client', Client)
    monkeypatch.setenv('OPENAI_API_KEY','must-not-use')
    assert HTTPProvider('model','synthetic-own-key', provider=provider, base_url='https://example.com/v1').discover_models() == []


def test_custom_ciphertext_cannot_move_between_endpoints(setup, monkeypatch):
    engine, left, _, _ = setup
    monkeypatch.setattr(llm, 'build_ai_provider', lambda *a, **k: SimpleNamespace(test_connection=lambda: None))
    saved = left.put('/api/v1/llm/config', json={'provider':'custom','base_url':'https://example.com/v1','model':'vendor/model:v1','api_key':'synthetic-key'}).json()['data']
    with Session(engine) as db:
        db.execute(update(WorkspaceLLMConfiguration).where(WorkspaceLLMConfiguration.id == saved['id']).values(base_url='https://other.example/v1'))
        db.commit()
    assert not left.get('/api/v1/llm/config').json()['data']['configured']


def test_mixed_public_and_private_dns_is_rejected(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a, **k: [(2,1,6,'',('8.8.8.8',443)),(2,1,6,'',('127.0.0.1',443))])
    with PublicEndpointTransport() as transport:
        with pytest.raises(LLMRequestError): transport.handle_request(httpx.Request('GET','https://example.com/models'))


def test_fresh_import_and_routes_with_storage_missing(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    from cryptography.fernet import Fernet
    env = os.environ | {
        'ENVIRONMENT':'development', 'VERCEL':'0', 'DEBUG':'false',
        'DATABASE_URL':'sqlite:///' + (tmp_path / 'startup.db').as_posix(),
        'DIRECT_DATABASE_URL':'', 'STORAGE_PROVIDER':'s3', 'STORAGE_BUCKET':'',
        'STORAGE_ACCESS_KEY_ID':'', 'STORAGE_SECRET_ACCESS_KEY':'',
        'LLM_ENCRYPTION_KEY':Fernet.generate_key().decode(),
        'ALLOWED_CORS_ORIGINS':'https://clinicalai-kappa.vercel.app',
    }
    code = '''
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    assert client.get('/api/v1/health').status_code == 200
    assert client.get('/api/v1/readiness').status_code == 503
    assert client.get('/openapi.json').status_code == 200
    assert len(client.get('/api/v1/llm/providers').json()['data']) == 6
    assert len(client.get('/api/v1/llm/metadata').json()['data']) == 6
    headers = {'origin':'https://clinicalai-kappa.vercel.app','x-clinicalai-request':'1'}
    assert client.post('/api/v1/workspace',headers=headers).status_code == 204
    cookies = dict(client.cookies)
    assert client.post('/api/v1/workspace',headers=headers).status_code == 204
    assert dict(client.cookies) == cookies
    assert not client.get('/api/v1/llm/config').json()['data']['configured']
    assert client.get('/api/v1/llm/configs').json()['data'] == []
'''
    result = subprocess.run([sys.executable,'-c',code], cwd=Path(__file__).resolve().parents[2]/'backend', env=env, capture_output=True,text=True)
    assert result.returncode == 0, result.stdout + result.stderr
