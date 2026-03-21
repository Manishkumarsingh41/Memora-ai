from services import database, memory


def test_save_and_list_files(tmp_db):
    database.save_file_metadata("u1", "doc1.pdf", "pdf", "drive1", "documents")
    database.save_file_metadata("u1", "img1.png", "image", "drive2", "images")
    files = database.list_files("u1")
    assert len(files) == 2
    assert {f["file_name"] for f in files} == {"doc1.pdf", "img1.png"}


def test_find_files_by_name_exact(tmp_db):
    database.save_file_metadata("u1", "QuarterlyReport.pdf", "pdf", "d1", "documents")
    matches = database.find_files_by_name("u1", "QuarterlyReport.pdf")
    assert len(matches) == 1
    assert matches[0]["file_name"] == "QuarterlyReport.pdf"


def test_find_files_by_name_partial(tmp_db):
    database.save_file_metadata("u1", "meeting-notes.pdf", "pdf", "d1", "documents")
    database.save_file_metadata("u1", "weekly_notes.txt", "pdf", "d2", "documents")
    matches = database.find_files_by_name("u1", "notes")
    assert len(matches) == 2


def test_find_files_by_name_no_match(tmp_db):
    database.save_file_metadata("u1", "invoice-2025.pdf", "pdf", "d1", "documents")
    matches = database.find_files_by_name("u1", "resume")
    assert matches == []


def test_get_file_by_id(tmp_db):
    file_id = database.save_file_metadata("u1", "contract.pdf", "pdf", "d1", "documents")
    row = database.get_file_by_id(file_id, "u1")
    assert row is not None
    assert row["file_name"] == "contract.pdf"


def test_get_file_by_id_wrong_user(tmp_db):
    file_id = database.save_file_metadata("u1", "private.pdf", "pdf", "d1", "documents")
    row = database.get_file_by_id(file_id, "u2")
    assert row is None


def test_get_recent_file(tmp_db):
    database.save_file_metadata("u1", "older.pdf", "pdf", "d1", "documents")
    database.save_file_metadata("u1", "newer.pdf", "pdf", "d2", "documents")
    files = database.list_files("u1")
    assert files[0]["file_name"] == "newer.pdf"


def test_add_and_get_memory(tmp_db):
    memory.add_memory("u1", "user", "hello")
    memory.add_memory("u1", "assistant", "hi")
    rows = memory.get_memory("u1")
    assert len(rows) == 2
    assert rows[0]["content"] == "hello"
    assert rows[1]["content"] == "hi"


def test_get_memory_limit(tmp_db):
    for idx in range(5):
        memory.add_memory("u1", "user", f"msg {idx}")
    rows = memory.get_memory("u1", limit=3)
    assert len(rows) == 3
    assert rows[0]["content"] == "msg 0"


def test_memory_isolated_by_user(tmp_db):
    memory.add_memory("u1", "user", "u1 message")
    memory.add_memory("u2", "user", "u2 message")
    u1_rows = memory.get_memory("u1")
    u2_rows = memory.get_memory("u2")
    assert len(u1_rows) == 1
    assert len(u2_rows) == 1
    assert u1_rows[0]["content"] == "u1 message"
    assert u2_rows[0]["content"] == "u2 message"
