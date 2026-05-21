import importlib


def test_rag_index_redacts_documents_and_metadata(monkeypatch):
    required_settings = {
        "OPENROUTER_API_KEY": "test",
        "JIRA_BASE_URL": "https://jira.test",
        "JIRA_EMAIL": "qa@example.com",
        "JIRA_TOKEN": "jira-token",
        "TELEGRAM_BOT_TOKEN": "telegram-token",
        "TELEGRAM_QA_LEADS_CHAT_ID": "1",
        "TELEGRAM_QA_TEAM_CHAT_ID": "2",
        "TELEGRAM_QA_OPS_CHAT_ID": "3",
        "TELEGRAM_QA_BUGS_CHAT_ID": "4",
    }
    for key, value in required_settings.items():
        monkeypatch.setenv(key, value)

    rag_module = importlib.import_module("knowledge_base.rag_engine")
    engine = rag_module.RAGEngine.__new__(rag_module.RAGEngine)
    captured = {}

    class FakeCollection:
        def upsert(self, documents, ids, metadatas):
            captured["documents"] = documents
            captured["ids"] = ids
            captured["metadatas"] = metadatas

    monkeypatch.setattr(engine, "_get_collection", lambda _name: FakeCollection())

    engine.index(
        documents=[
            "Authorization: Bearer secret-token\n"
            "email qa.user@example.com\n"
            "password=hunter2"
        ],
        ids=["doc-1"],
        metadatas=[{
            "source": "raw qa.user@example.com",
            "type": "debug_resolution",
        }],
    )

    indexed_doc = captured["documents"][0]
    indexed_meta = captured["metadatas"][0]
    assert "secret-token" not in indexed_doc
    assert "qa.user@example.com" not in indexed_doc
    assert "hunter2" not in indexed_doc
    assert "qa.user@example.com" not in indexed_meta["source"]
    assert "redactions_applied" in indexed_meta
