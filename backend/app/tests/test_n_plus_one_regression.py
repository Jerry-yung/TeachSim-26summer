"""测试 _get_session_or_404 / _get_session_with_lesson 使用 joinedload 消除 N+1 查询。

回归保护：以前 _get_session_or_404 用 db.get(...) 不带 joinedload，
访问 session.lesson.xxx 时会触发额外的 lazy-load SQL（N+1 模式）。
"""

import uuid
from unittest.mock import MagicMock

# 必须导入所有 model 让 SQLAlchemy mapper 初始化通过
from app.models import lesson as _lesson  # noqa: F401
from app.models import session_student as _ss  # noqa: F401
from app.models import teacher as _t  # noqa: F401
from app.models.lesson import ClassroomSession  # noqa: E402


def test_inclass_session_query_uses_joinedload():
    """构造与生产代码一致的 query，编译成 PG SQL，检查必须含 JOIN lessons。"""
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.orm import Query, joinedload

    sid = uuid.uuid4()
    query = Query([ClassroomSession]).options(
        joinedload(ClassroomSession.lesson)
    ).filter(ClassroomSession.id == sid)

    compiled = str(
        query.statement.compile(dialect=postgresql.dialect())
    ).lower()

    assert "join lessons" in compiled, (
        f"query 没有 JOIN lessons —— joinedload 未生效，N+1 回归！\n"
        f"实际 SQL: {compiled}"
    )


def test_inclass_get_session_or_404_returns_session_with_lesson_loaded():
    """检查 inclass.py 源码中 _get_session_or_404 包含 joinedload 调用（防回滚）。"""
    import inspect
    from pathlib import Path

    # 读源码而不是导入模块，避免 Python 3.9 解析失败
    src = (Path(__file__).parent.parent / "api" / "routes" / "inclass.py").read_text()
    # 简单字符串检查：函数体内必须包含 joinedload(ClassroomSession.lesson)
    assert "_get_session_or_404" in src
    # 找函数体
    func_start = src.index("def _get_session_or_404")
    func_section = src[func_start:func_start + 1500]
    assert "joinedload" in func_section, (
        "_get_session_or_404 缺少 joinedload —— N+1 回归！"
    )
    assert "ClassroomSession.lesson" in func_section, (
        "_get_session_or_404 应 joinedload(ClassroomSession.lesson)"
    )


def test_report_get_session_with_lesson_uses_joinedload():
    """report.py:_get_session_with_lesson 同样必须用 joinedload —— 通过编译 SQL 验证。"""
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.orm import Query, joinedload

    sid = uuid.uuid4()
    # 与 report.py:_get_session_with_lesson 的查询保持一致
    query = Query([ClassroomSession]).options(
        joinedload(ClassroomSession.lesson)
    ).filter(ClassroomSession.id == sid)

    compiled = str(
        query.statement.compile(dialect=postgresql.dialect())
    ).lower()

    assert "join lessons" in compiled, (
        f"report.py 的 query 没有 JOIN lessons！\n实际 SQL: {compiled}"
    )


def test_inclass_get_session_or_404_raises_404_when_missing():
    """检查 inclass.py 源码：404 错误处理保留。"""
    from pathlib import Path

    src = (Path(__file__).parent.parent / "api" / "routes" / "inclass.py").read_text()
    func_start = src.index("def _get_session_or_404")
    func_section = src[func_start:func_start + 1500]
    assert "status_code=404" in func_section
    assert 'detail="session 不存在"' in func_section


def test_inclass_get_session_or_404_raises_403_for_wrong_teacher():
    """检查 inclass.py 源码：403 鉴权保留。"""
    from pathlib import Path

    src = (Path(__file__).parent.parent / "api" / "routes" / "inclass.py").read_text()
    func_start = src.index("def _get_session_or_404")
    func_section = src[func_start:func_start + 1500]
    assert "status_code=403" in func_section
    assert 'detail="无权访问该课堂"' in func_section
    assert "_LEGACY_TEACHER_ID" in func_section
