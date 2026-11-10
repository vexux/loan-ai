import pytest
from contracts.adapters.data_adapter_contract import DataQuery
from components.data_adapters.sqlite_adapter import SQLiteDataAdapter

DB_PATH = "data/banking.db"


@pytest.mark.asyncio
async def test_sqlite_get_customer_by_id():
    adapter = SQLiteDataAdapter(db_path=DB_PATH)
    result = await adapter.get_by_id(resource="customers", resource_id="C001")

    assert result.success is True
    assert result.data is not None
    assert len(result.data.records) == 1
    assert result.data.records[0]["customer_id"] == "C001"
    assert result.data.records[0]["name"] == "Alice Sharma"


@pytest.mark.asyncio
async def test_sqlite_get_nonexistent_id():
    adapter = SQLiteDataAdapter(db_path=DB_PATH)
    result = await adapter.get_by_id(resource="customers", resource_id="C999")

    assert result.success is False
    assert result.data.total == 0


@pytest.mark.asyncio
async def test_sqlite_query_with_filters():
    adapter = SQLiteDataAdapter(db_path=DB_PATH)
    query = DataQuery(resource="customers", filters={"account_status": "active"})
    result = await adapter.query(query)

    assert result.success is True
    assert result.data.total >= 3
    for record in result.data.records:
        assert record["account_status"] == "active"
