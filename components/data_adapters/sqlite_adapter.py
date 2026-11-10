import os
import sqlite3
from typing import Any

from contracts.adapters.data_adapter_contract import DataAdapterContract, DataQuery, DataResult
from contracts.common.enums import ExecutionStatus
from contracts.common.execution_result import ExecutionResult

DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "banking.db"
)


class SQLiteDataAdapter(DataAdapterContract):
    """
    Domain-Agnostic, Enterprise SQLite Data Adapter.
    Permanently immune to SQL injection through Schema Introspection:
    - Tables are verified against the real database schema (sqlite_master).
    - Filter columns are verified against the real table columns (PRAGMA table_info).
    - All queries use parameterized values.
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = os.path.abspath(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_valid_tables(self, conn: sqlite3.Connection) -> set[str]:
        """Introspects the live database to return all valid user table names."""
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        return {row[0] for row in cur.fetchall()}

    def _get_table_columns(self, conn: sqlite3.Connection, table_name: str) -> list[dict]:
        """Returns verified column metadata for a validated table."""
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        return [dict(row) for row in cur.fetchall()]

    async def get_by_id(self, resource: str, resource_id: str) -> ExecutionResult[DataResult]:
        if not resource_id:
            return ExecutionResult(success=False, status=ExecutionStatus.FAILURE, data=DataResult())

        conn = self._connect()
        try:
            valid_tables = self._get_valid_tables(conn)
            if resource not in valid_tables:
                conn.close()
                return ExecutionResult(
                    success=False,
                    status=ExecutionStatus.FAILURE,
                    data=DataResult(errors=[f"Security violation: Unknown table '{resource}'."]),
                )

            columns = self._get_table_columns(conn, resource)
            if not columns:
                conn.close()
                return ExecutionResult(success=False, status=ExecutionStatus.FAILURE, data=DataResult())

            pk_col = next((c["name"] for c in columns if c["pk"] > 0), columns[0]["name"])

            cur = conn.cursor()
            cur.execute(f"SELECT * FROM {resource} WHERE {pk_col} = ?", (str(resource_id).strip(),))
            row = cur.fetchone()

            if row is None:
                text_cols = [c["name"] for c in columns if "TEXT" in c["type"].upper() or "CHAR" in c["type"].upper()]
                for col in text_cols:
                    cur.execute(
                        f"SELECT * FROM {resource} WHERE LOWER({col}) = ?",
                        (str(resource_id).lower().strip(),),
                    )
                    row = cur.fetchone()
                    if row is not None:
                        break

            conn.close()

            if row is None:
                return ExecutionResult(success=False, status=ExecutionStatus.FAILURE, data=DataResult())

            records = [dict(row)]
            return ExecutionResult(
                success=True,
                status=ExecutionStatus.SUCCESS,
                data=DataResult(records=records, total=1),
            )

        except Exception as e:
            conn.close()
            return ExecutionResult(success=False, status=ExecutionStatus.FAILURE, data=DataResult(errors=[str(e)]))

    async def query(self, request: DataQuery) -> ExecutionResult[DataResult]:
        conn = self._connect()
        try:
            valid_tables = self._get_valid_tables(conn)
            if request.resource not in valid_tables:
                conn.close()
                return ExecutionResult(
                    success=False,
                    status=ExecutionStatus.FAILURE,
                    data=DataResult(errors=[f"Security violation: Unknown table '{request.resource}'."]),
                )

            columns = self._get_table_columns(conn, request.resource)
            valid_column_names = {c["name"] for c in columns}

            where_clauses = []
            values = []
            for col, val in request.filters.items():
                if col not in valid_column_names:
                    conn.close()
                    return ExecutionResult(
                        success=False,
                        status=ExecutionStatus.FAILURE,
                        data=DataResult(errors=[f"Security violation: Unknown column '{col}' for table '{request.resource}'."]),
                    )
                where_clauses.append(f"{col} = ?")
                values.append(val)

            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            limit_val = max(1, min(int(request.limit), 1000))
            sql = f"SELECT * FROM {request.resource} {where_sql} LIMIT {limit_val}"

            cur = conn.cursor()
            cur.execute(sql, values)
            rows = cur.fetchall()
            conn.close()

            records = [dict(r) for r in rows]
            return ExecutionResult(
                success=True,
                status=ExecutionStatus.SUCCESS,
                data=DataResult(records=records, total=len(records)),
            )

        except Exception as e:
            conn.close()
            return ExecutionResult(success=False, status=ExecutionStatus.FAILURE, data=DataResult(errors=[str(e)]))

    async def insert_record(self, resource: str, data: dict[str, Any]) -> ExecutionResult[dict[str, Any]]:
        conn = self._connect()
        try:
            valid_tables = self._get_valid_tables(conn)
            if resource not in valid_tables:
                conn.close()
                return ExecutionResult(success=False, status=ExecutionStatus.FAILURE, data={"error": f"Unknown table '{resource}'."})

            columns = self._get_table_columns(conn, resource)
            valid_col_names = {c["name"] for c in columns}

            # Filter data strictly to columns that actually exist in the table
            safe_data = {k: v for k, v in data.items() if k in valid_col_names}
            if not safe_data:
                conn.close()
                return ExecutionResult(success=False, status=ExecutionStatus.FAILURE, data={"error": "No valid column data provided for insert."})

            cols = list(safe_data.keys())
            placeholders = ["?"] * len(cols)
            sql = f"INSERT INTO {resource} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"

            cur = conn.cursor()
            cur.execute(sql, list(safe_data.values()))
            conn.commit()
            conn.close()

            return ExecutionResult(
                success=True,
                status=ExecutionStatus.SUCCESS,
                data={"inserted_id": data.get("application_id") or data.get("id"), "resource": resource},
            )
        except sqlite3.IntegrityError as ie:
            conn.close()
            return ExecutionResult(success=False, status=ExecutionStatus.FAILURE, data={"error": f"Integrity error: {ie}"})
        except Exception as e:
            conn.close()
            return ExecutionResult(success=False, status=ExecutionStatus.FAILURE, data={"error": str(e)})

    async def execute_transaction(self, operations: list[dict[str, Any]]) -> ExecutionResult[dict[str, Any]]:
        if not operations:
            return ExecutionResult(success=False, status=ExecutionStatus.FAILURE, data={"error": "No operations supplied."})

        conn = self._connect()
        try:
            valid_tables = self._get_valid_tables(conn)
            cur = conn.cursor()
            cur.execute("BEGIN TRANSACTION")

            executed = []
            for op in operations:
                resource = op["resource"]
                if resource not in valid_tables:
                    raise ValueError(f"Unknown table '{resource}' in transaction.")

                columns = self._get_table_columns(conn, resource)
                valid_col_names = {c["name"] for c in columns}
                safe_data = {k: v for k, v in op["data"].items() if k in valid_col_names}

                cols = list(safe_data.keys())
                placeholders = ["?"] * len(cols)
                sql = f"INSERT INTO {resource} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"

                cur.execute(sql, list(safe_data.values()))
                executed.append({"resource": resource, "id": safe_data.get(f"{resource[:-1]}_id") or safe_data.get("id")})

            conn.commit()
            conn.close()

            return ExecutionResult(
                success=True,
                status=ExecutionStatus.SUCCESS,
                data={"status": "committed", "operations_count": len(executed), "records": executed},
            )
        except Exception as e:
            conn.rollback()
            conn.close()
            return ExecutionResult(success=False, status=ExecutionStatus.FAILURE, data={"error": f"Transaction rolled back: {str(e)}"})
