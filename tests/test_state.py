import json
import os
import tempfile

from etl.state import SyncState


def test_needs_sync_new_document():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        os.unlink(path)
        state = SyncState(path)
        assert state.needs_sync("google_docs", "doc1", "2026-01-01T00:00:00Z")
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_needs_sync_unchanged():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        os.unlink(path)
        state = SyncState(path)
        state.mark_synced("google_docs", "doc1", "Test", "2026-01-01T00:00:00Z")

        assert not state.needs_sync("google_docs", "doc1", "2026-01-01T00:00:00Z")
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_needs_sync_updated():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        os.unlink(path)
        state = SyncState(path)
        state.mark_synced("google_docs", "doc1", "Test", "2026-01-01T00:00:00Z")

        assert state.needs_sync("google_docs", "doc1", "2026-06-01T00:00:00Z")
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_persistence():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        os.unlink(path)
        state = SyncState(path)
        state.mark_synced("google_docs", "doc1", "Test", "2026-01-01T00:00:00Z")
        state.save()

        # Reload
        state2 = SyncState(path)
        assert not state2.needs_sync("google_docs", "doc1", "2026-01-01T00:00:00Z")
        assert state2.needs_sync("google_docs", "doc1", "2026-06-01T00:00:00Z")
    finally:
        if os.path.exists(path):
            os.unlink(path)
