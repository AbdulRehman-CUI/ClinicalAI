"""Live local PostgreSQL checks; never point these at a deployed database."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
from pathlib import Path
from secrets import token_urlsafe
import subprocess
import sys
from uuid import uuid4

from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import WorkspaceLLMConfiguration
from app.services import llm
from app.services.exceptions import LLMRequestError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def postgres_database():
    import psycopg
    from psycopg import sql
    source = os.environ.get('TEST_POSTGRES_ADMIN_URL')
    if not source:
        pytest.skip('requires an isolated local PostgreSQL admin URL')
    url = make_url(source)
    assert url.host in {'127.0.0.1', 'localhost'}, 'Only a local test server is allowed'
    name = 'clinicalai_verify_' + uuid4().hex
    admin_url = url.set(drivername='postgresql', database='postgres').render_as_string(hide_password=False)
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    target = url.set(drivername='postgresql+psycopg', database=name).render_as_string(hide_password=False)
    try:
        yield target
    finally:
        with psycopg.connect(admin_url, autocommit=True) as connection:
            connection.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))


def migrate(url, revision='head'):
    config = Config(str(ROOT / 'backend/alembic.ini'))
    config.attributes.update(database_url=url, configure_logger=False)
    command.upgrade(config, revision)


def test_existing_postgres_configuration_migration(postgres_database, monkeypatch):
    migrate(postgres_database, '20261112_0002')
    engine = create_engine(postgres_database)
    encryption_key = Fernet.generate_key()
    cipher = Fernet(encryption_key)
    settings = get_settings().model_copy(update={'llm_encryption_key': encryption_key.decode()})
    monkeypatch.setattr(llm, 'get_settings', lambda: settings)
    now = datetime.now(timezone.utc)
    rows = []
    with engine.begin() as db:
        for kind in ('session', 'remember', 'expired_key', 'expired_workspace'):
            owner, token = uuid4().hex, token_urlsafe(32)
            session_hash = sha256(token.encode()).hexdigest() if kind == 'session' else None
            expiry = now + (timedelta(days=-1) if kind == 'expired_key' else timedelta(days=7))
            workspace_expiry = now + (timedelta(days=-1) if kind == 'expired_workspace' else timedelta(days=30))
            ciphertext = cipher.encrypt(llm._binding(owner, 'openai', 'gpt-4.1-mini') + b'synthetic-legacy-key').decode()
            row = dict(owner=owner, digest=sha256(token_urlsafe(32).encode()).hexdigest(),
                       workspace_expiry=workspace_expiry, ciphertext=ciphertext, session_hash=session_hash, expiry=expiry)
            rows.append(row | {'kind': kind})
            db.execute(text('INSERT INTO guest_workspaces (id, credential_hash, expires_at) VALUES (:owner,:digest,:workspace_expiry)'), row)
            db.execute(text("INSERT INTO workspace_llm_configurations (workspace_id,provider,model,encrypted_api_key,session_hash,expires_at) VALUES (:owner,'openai','gpt-4.1-mini',:ciphertext,:session_hash,:expiry)"), row)
    migrate(postgres_database)
    with Session(engine) as db:
        assert db.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '20261120_0001'
        assert db.query(WorkspaceLLMConfiguration).count() == 4
        for row in rows:
            saved = db.get(WorkspaceLLMConfiguration, row['owner'])
            assert saved.workspace_id == saved.id == row['owner'] and saved.active
            assert saved.encrypted_api_key == row['ciphertext']
            assert saved.session_hash == row['session_hash'] and saved.expires_at == row['expiry']
            assert llm._decrypt(saved) == 'synthetic-legacy-key'
            db.info.update(workspace_id=saved.workspace_id, llm_session_hash=row['session_hash'])
            if row['kind'] == 'expired_key':
                with pytest.raises(LLMRequestError): llm.require_configuration(db)
            else:
                assert llm.require_configuration(db) == ('openai','gpt-4.1-mini','synthetic-legacy-key')
            if row['kind'] == 'session':
                db.info['llm_session_hash'] = None
                assert not llm.configuration_status(db).configured
                db.info['llm_session_hash'] = row['session_hash']
                assert llm.configuration_status(db).configured
            if row['kind'] == 'expired_workspace':
                with pytest.raises(LLMRequestError): llm.configured_provider(db)
        # An old-version upsert no longer has its unique conflict target.
        with pytest.raises(ProgrammingError):
            db.execute(text("INSERT INTO workspace_llm_configurations (workspace_id,provider,model,encrypted_api_key,expires_at) VALUES (:owner,'openai','gpt-4.1-mini','synthetic',:expiry) ON CONFLICT (workspace_id) DO UPDATE SET model=excluded.model"), rows[0])
        db.rollback()
        # Duplicate active selections are rejected by PostgreSQL itself.
        with pytest.raises(IntegrityError):
            db.execute(text("INSERT INTO workspace_llm_configurations (id,workspace_id,active,provider,model,encrypted_api_key,expires_at) VALUES (:id,:owner,true,'openai','gpt-4.1-mini','synthetic',:expiry)"), rows[0] | {'id':uuid4().hex})
        db.rollback()
    # Exercise edits and explicit selection against the migrated PostgreSQL schema.
    from types import SimpleNamespace
    monkeypatch.setattr(llm, 'build_ai_provider', lambda *a, **k: SimpleNamespace(test_connection=lambda: None))
    remembered = next(row for row in rows if row['kind'] == 'remember')
    with Session(engine) as db:
        db.info.update(workspace_id=remembered['owner'], llm_session_hash=None)
        added, _ = llm.save_configuration(db, llm.LLMSave(provider='gemini', model='gemini-3.6-flash', api_key='synthetic-new-key', remember=True))
        assert not added.active
        assert llm.configuration_status(db).id == remembered['owner']
        assert llm.activate_configuration(db, added.id).id == added.id
        assert llm.require_configuration(db) == ('gemini', 'gemini-3.6-flash', 'synthetic-new-key')
        assert llm.activate_configuration(db, remembered['owner']).id == remembered['owner']
        assert llm.require_configuration(db)[2] == 'synthetic-legacy-key'
        llm.remove_configuration(db, added.id)
        assert llm.configuration_status(db).configured
    engine.dispose()


def test_fresh_postgres_production_startup_missing_storage(postgres_database):
    migrate(postgres_database)
    env = os.environ | {
        'VERCEL':'1', 'ENVIRONMENT':'production', 'DEBUG':'false',
        'DATABASE_URL':postgres_database, 'DIRECT_DATABASE_URL':'',
        'WORKSPACE_SIGNING_SECRET':token_urlsafe(32), 'LLM_ENCRYPTION_KEY':Fernet.generate_key().decode(),
        'FRONTEND_URL':'https://clinicalai-kappa.vercel.app', 'ALLOWED_CORS_ORIGINS':'https://clinicalai-kappa.vercel.app',
        'STORAGE_PROVIDER':'s3', 'STORAGE_BUCKET':'', 'STORAGE_ACCESS_KEY_ID':'', 'STORAGE_SECRET_ACCESS_KEY':'',
    }
    code = '''
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.db.session import engine
origin = 'https://clinicalai-kappa.vercel.app'
headers = {'Origin':origin, 'X-ClinicalAI-Request':'1'}
with TestClient(app, base_url=origin) as left, TestClient(app, base_url=origin) as right:
    for path in ('/api/v1/health','/openapi.json','/api/v1/llm/providers','/api/v1/llm/metadata'):
        assert left.get(path).status_code == 200
    readiness = left.get('/api/v1/readiness')
    assert readiness.status_code == 503
    assert readiness.json()['database']['ready']
    assert not readiness.json()['storage']['configured']
    for name in ('STORAGE_BUCKET','STORAGE_ACCESS_KEY_ID','STORAGE_SECRET_ACCESS_KEY'):
        assert name in str(readiness.json()['storage']['issues'])
    assert left.post('/api/v1/workspace').status_code == 403
    assert left.post('/api/v1/workspace',headers=headers | {'Origin':'https://evil.example'}).status_code == 403
    created = left.post('/api/v1/workspace',headers=headers)
    assert created.status_code == 204
    cookie = created.headers['set-cookie']
    assert '__Host-clinicalai-workspace=' in cookie
    assert all(flag in cookie for flag in ('Secure','HttpOnly','Path=/','SameSite=lax')) and 'Domain=' not in cookie
    original = dict(left.cookies)
    assert left.post('/api/v1/workspace',headers=headers).status_code == 204
    assert dict(left.cookies) == original
    assert right.post('/api/v1/workspace',headers=headers).status_code == 204
    assert dict(right.cookies) != original
    assert left.get('/api/v1/llm/configs').json()['data'] == []
    patient = left.post('/api/v1/patients',headers=headers,json={'first_name':'Synthetic','last_name':'Verification','age':30,'biological_sex':'Female','blood_group':'A+','height_cm':165,'weight_kg':60})
    assert patient.status_code == 201, patient.text
    pid = patient.json()['data']['id']
    assert right.get(f'/api/v1/patients/{pid}').status_code == 404
    upload = left.post(f'/api/v1/patients/{pid}/reports',headers=headers,files={'file':('synthetic.txt',b'synthetic report','text/plain')})
    assert upload.status_code == 503
    assert upload.json()['message'] == 'Report storage is not configured. Contact your administrator.'
    assert 'Traceback' not in upload.text and 'postgresql' not in upload.text
    intent = left.post(f'/api/v1/patients/{pid}/reports/upload-intent',headers=headers,json={'filename':'synthetic.txt','size':16})
    assert intent.status_code == 503 and intent.json()['message'] == upload.json()['message']
    with engine.connect() as db:
        assert db.execute(text('SELECT count(*) FROM medical_reports')).scalar_one() == 0
    assert not left.get('/api/v1/llm/config').json()['data']['configured']
'''
    result = subprocess.run([sys.executable,'-c',code],cwd=ROOT/'backend',env=env,capture_output=True,text=True,timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
