from pathlib import Path


def test_metals_freshness_methodology_history_workflow_is_manual_and_read_only():
    workflow = Path('.github/workflows/metals-freshness-methodology-history-audit.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in workflow
    assert 'schedule:' not in workflow
    assert 'fetch-depth: 0' in workflow
    assert 'contents: read' in workflow


def test_metals_freshness_methodology_history_audit_has_no_database_or_collection_paths():
    script = Path('scripts/audit_metals_freshness_methodology_history.py').read_text(encoding='utf-8')
    assert 'LOCAL_GIT_HISTORY_READ_ONLY' in script
    assert 'postgres_write_performed' in script
    assert 'publication_staged' in script
    assert 'publication_activated' in script
    assert 'source_collection_performed' in script
    assert 'psycopg' not in script
    assert 'requests.' not in script
