"""
Supabase client for sync operations
"""

from typing import Any, Dict, List, Optional
from supabase import create_client, Client
import structlog

from ..config import settings
from .logger import get_logger
from .retry_utils import retry_with_exponential_backoff, create_retry_config

logger = get_logger(__name__)


class SupabaseClient:
    """Client for interacting with Supabase"""

    def __init__(self):
        self.url = settings.supabase_url
        self.key = settings.supabase_service_role_key
        # Create client with minimal options to avoid compatibility issues
        try:
            self.client: Client = create_client(self.url, self.key)
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
            # Create a mock client for testing
            self.client = None

    async def get_record(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record from Supabase"""

        async def _get_record():
            response = (
                self.client.table(table).select("*").eq("id", record_id).execute()
            )
            if response.data:
                return response.data[0]
            return None

        try:
            return await retry_with_exponential_backoff(
                _get_record,
                retry_config=create_retry_config(max_retries=3, base_delay=1.0),
            )
        except Exception as e:
            logger.error(
                "Failed to get record", table=table, record_id=record_id, error=str(e)
            )
            raise

    async def get_records(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get multiple records from Supabase"""

        async def _get_records():
            query = self.client.table(table).select(
                "*" if not columns else ",".join(columns)
            )

            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            query = query.limit(limit)
            response = query.execute()
            return response.data

        try:
            return await retry_with_exponential_backoff(
                _get_records,
                retry_config=create_retry_config(max_retries=3, base_delay=1.0),
            )
        except Exception as e:
            logger.error(
                "Failed to get records", table=table, filters=filters, error=str(e)
            )
            raise

    async def create_record(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record in Supabase"""
        # Debug logging to see what data is actually being sent
        logger.info(f"Supabase create_record called with data: {data}")

        async def _create_record():
            response = self.client.table(table).insert(data).execute()
            if response.data:
                return response.data[0]
            raise Exception("No data returned from insert operation")

        try:
            return await retry_with_exponential_backoff(
                _create_record,
                retry_config=create_retry_config(max_retries=3, base_delay=1.0),
            )
        except Exception as e:
            logger.error(
                "Failed to create record", table=table, data=data, error=str(e)
            )
            raise

    async def insert_data(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert data into Supabase table (alias for create_record)"""
        return await self.create_record(table, data)

    async def update_record(
        self, table: str, record_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing record in Supabase"""

        async def _update_record():
            response = (
                self.client.table(table).update(data).eq("id", record_id).execute()
            )
            if response.data:
                return response.data[0]
            raise Exception("No data returned from update operation")

        try:
            return await retry_with_exponential_backoff(
                _update_record,
                retry_config=create_retry_config(max_retries=3, base_delay=1.0),
            )
        except Exception as e:
            logger.error(
                "Failed to update record",
                table=table,
                record_id=record_id,
                data=data,
                error=str(e),
            )
            raise

    async def delete_record(self, table: str, record_id: str) -> bool:
        """Delete a record from Supabase"""

        async def _delete_record():
            response = self.client.table(table).delete().eq("id", record_id).execute()
            return True

        try:
            return await retry_with_exponential_backoff(
                _delete_record,
                retry_config=create_retry_config(max_retries=3, base_delay=1.0),
            )
        except Exception as e:
            logger.error(
                "Failed to delete record",
                table=table,
                record_id=record_id,
                error=str(e),
            )
            raise

    async def upsert_record(
        self, table: str, data: Dict[str, Any], on_conflict: str = "id"
    ) -> Dict[str, Any]:
        """Upsert (insert or update) a record in Supabase"""

        async def _upsert_record():
            response = (
                self.client.table(table).upsert(data, on_conflict=on_conflict).execute()
            )
            if response.data:
                return response.data[0]
            raise Exception("No data returned from upsert operation")

        try:
            return await retry_with_exponential_backoff(
                _upsert_record,
                retry_config=create_retry_config(max_retries=3, base_delay=1.0),
            )
        except Exception as e:
            logger.error(
                "Failed to upsert record", table=table, data=data, error=str(e)
            )
            raise

    async def find_record_by_field(
        self, table: str, field: str, value: str
    ) -> Optional[Dict[str, Any]]:
        """Find a record by a specific field value"""

        async def _find_record_by_field():
            response = (
                self.client.table(table).select("*").eq(field, value).limit(1).execute()
            )
            if response.data:
                return response.data[0]
            return None

        try:
            return await retry_with_exponential_backoff(
                _find_record_by_field,
                retry_config=create_retry_config(max_retries=3, base_delay=1.0),
            )
        except Exception as e:
            logger.error(
                "Failed to find record by field",
                table=table,
                field=field,
                value=value,
                error=str(e),
            )
            return None

    async def search_records(
        self, table: str, search_term: str, columns: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search records in Supabase using text search"""
        try:
            query = self.client.table(table).select(
                "*" if not columns else ",".join(columns)
            )
            # Note: This is a basic implementation. Supabase text search requires specific setup
            response = query.ilike("name", f"%{search_term}%").execute()
            return response.data
        except Exception as e:
            logger.error(
                "Failed to search records",
                table=table,
                search_term=search_term,
                error=str(e),
            )
            return []

    async def count_records(
        self, table: str, filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count records in Supabase table"""
        try:
            query = self.client.table(table).select("id", count="exact")

            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            response = query.execute()
            return response.count or 0
        except Exception as e:
            logger.error(
                "Failed to count records", table=table, filters=filters, error=str(e)
            )
            return 0

    async def update_record(
        self, table: str, record_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a record in Supabase table"""
        try:
            response = await retry_with_exponential_backoff(
                self._update_record,
                table,
                record_id,
                data,
                config=create_retry_config(max_retries=4),
            )
            return response
        except Exception as e:
            logger.error(
                "Failed to update record",
                table=table,
                record_id=record_id,
                data=data,
                error=str(e),
            )
            return None

    async def _update_record(
        self, table: str, record_id: str, data: Dict[str, Any], **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Internal method to update a record"""
        response = self.client.table(table).update(data).eq("id", record_id).execute()
        if response.data:
            return response.data[0]
        return None

    async def delete_record(self, table: str, record_id: str) -> bool:
        """Delete a record from Supabase table"""
        try:
            response = await retry_with_exponential_backoff(
                self._delete_record,
                table,
                record_id,
                config=create_retry_config(max_retries=4),
            )
            return response
        except Exception as e:
            logger.error(
                "Failed to delete record",
                table=table,
                record_id=record_id,
                error=str(e),
            )
            return False

    async def _delete_record(self, table: str, record_id: str, **kwargs) -> bool:
        """Internal method to delete a record"""
        response = self.client.table(table).delete().eq("id", record_id).execute()
        return True

    async def get_documents(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get multiple documents from Supabase table"""

        async def _get_documents():
            # Start with base query and select
            if fields:
                query = self.client.table(table).select(",".join(fields))
            else:
                query = self.client.table(table).select("*")

            if filters:
                # Handle both dictionary and list formats
                if isinstance(filters, dict):
                    # Dictionary format: {"field": "value"}
                    for field, value in filters.items():
                        query = query.eq(field, value)
                elif isinstance(filters, list):
                    # List format: [["field", "=", "value"]]
                    for filter_condition in filters:
                        if len(filter_condition) == 3:
                            field, operator, value = filter_condition
                            if operator == "=":
                                query = query.eq(field, value)
                            elif operator == "!=":
                                query = query.neq(field, value)
                            elif operator == ">":
                                query = query.gt(field, value)
                            elif operator == ">=":
                                query = query.gte(field, value)
                            elif operator == "<":
                                query = query.lt(field, value)
                            elif operator == "<=":
                                query = query.lte(field, value)
                            elif operator == "in":
                                query = query.in_(field, value)
                            elif operator == "like":
                                query = query.like(field, value)

            # Apply limit
            query = query.limit(limit)

            response = query.execute()
            return response.data

        try:
            return await retry_with_exponential_backoff(
                _get_documents, retry_config=create_retry_config(max_retries=4)
            )
        except Exception as e:
            logger.error("Failed to get documents", table=table, error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check if Supabase connection is healthy"""
        try:
            if not self.client:
                return False

            # Try to get a simple record to test connection
            response = self.client.table("users").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error("Supabase health check failed", error=str(e))
            return False
