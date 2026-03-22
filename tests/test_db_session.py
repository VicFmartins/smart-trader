from __future__ import annotations

import pytest

from app.db import session as session_module


class FakeSession:
    def __init__(self) -> None:
        self.rollback_called = False
        self.close_called = False

    def rollback(self) -> None:
        self.rollback_called = True

    def close(self) -> None:
        self.close_called = True


def test_get_db_rolls_back_and_closes_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = FakeSession()

    monkeypatch.setattr(session_module, "get_session_factory", lambda: (lambda: fake_session))

    generator = session_module.get_db()
    yielded = next(generator)
    assert yielded is fake_session

    with pytest.raises(RuntimeError, match="boom"):
        generator.throw(RuntimeError("boom"))

    assert fake_session.rollback_called is True
    assert fake_session.close_called is True

