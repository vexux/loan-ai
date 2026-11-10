from collections import OrderedDict
from uuid import uuid4
from typing import Optional

from contracts.common.enums import ExecutionStatus
from contracts.common.execution_result import ExecutionResult
from contracts.memory.memory_contract import MemoryContract, MemoryRecord, MemoryRequest


class InMemoryMemoryStore(MemoryContract):
    """
    Production-grade in-memory dialogue store with bounded session retention (LRU)
    and per-session record limits to eliminate memory leaks.
    """

    def __init__(
        self,
        max_sessions: int = 500,
        max_records_per_session: int = 50,
    ) -> None:
        self.max_sessions = max_sessions
        self.max_records_per_session = max_records_per_session
        # Map: session_id -> list of MemoryRecord
        self._sessions: OrderedDict[str, list[MemoryRecord]] = OrderedDict()

    async def save(self, record: MemoryRecord) -> ExecutionResult[MemoryRecord]:
        if not record.memory_id:
            record.memory_id = str(uuid4())

        session_id = record.session_id or "default"

        # LRU management: Move accessed session to end
        if session_id in self._sessions:
            self._sessions.move_to_end(session_id)
        else:
            if len(self._sessions) >= self.max_sessions:
                # Evict oldest session
                self._sessions.popitem(last=False)
            self._sessions[session_id] = []

        records = self._sessions[session_id]
        records.append(record)

        # Enforce per-session sliding window
        if len(records) > self.max_records_per_session:
            self._sessions[session_id] = records[-self.max_records_per_session:]

        return ExecutionResult(success=True, status=ExecutionStatus.SUCCESS, data=record)

    async def retrieve(self, request: MemoryRequest) -> ExecutionResult[list[MemoryRecord]]:
        session_id = request.session_id or "default"
        records = self._sessions.get(session_id, [])

        if session_id in self._sessions:
            self._sessions.move_to_end(session_id)

        filtered = records
        if request.user_id:
            filtered = [r for r in filtered if r.user_id == request.user_id]

        if request.memory_type:
            filtered = [r for r in filtered if r.memory_type == request.memory_type]

        limit = request.limit if request.limit > 0 else 10
        results = filtered[-limit:]
        return ExecutionResult(success=True, status=ExecutionStatus.SUCCESS, data=results)

    async def delete(self, memory_id: str) -> ExecutionResult[None]:
        for session_id, records in self._sessions.items():
            self._sessions[session_id] = [r for r in records if r.memory_id != memory_id]
        return ExecutionResult(success=True, status=ExecutionStatus.SUCCESS, data=None)

    async def clear_session(self, session_id: str) -> ExecutionResult[None]:
        """Explicitly purges an entire session from memory."""
        if session_id in self._sessions:
            del self._sessions[session_id]
        return ExecutionResult(success=True, status=ExecutionStatus.SUCCESS, data=None)

    def get_active_session_count(self) -> int:
        return len(self._sessions)

    async def get_dialogue_history(self, session_id: str, limit: int = 6) -> str:
        if not session_id:
            return ""

        res = await self.retrieve(MemoryRequest(session_id=session_id, limit=limit))
        if not res.success or not res.data:
            return ""

        formatted_lines = []
        for rec in res.data:
            speaker = rec.metadata.get("speaker", "User")
            formatted_lines.append(f"{speaker}: {rec.content}")

        return "\n".join(formatted_lines)