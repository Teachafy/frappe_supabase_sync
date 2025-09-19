"""
Supabase client for sync operations
"""
from typing import Any, Dict, List, Optional
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from ..config import settings
from .logger import get_logger

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
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_record(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record from Supabase"""
        try:
            response = self.client.table(table).select("*").eq("id", record_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error("Failed to get record", table=table, record_id=record_id, error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_records(self, table: str, filters: Optional[Dict[str, Any]] = None,
                         columns: Optional[List[str]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get multiple records from Supabase"""
        try:
            query = self.client.table(table).select("*" if not columns else ",".join(columns))
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            query = query.limit(limit)
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error("Failed to get records", table=table, filters=filters, error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def create_record(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record in Supabase"""
        try:
            response = self.client.table(table).insert(data).execute()
            if response.data:
                return response.data[0]
            raise Exception("No data returned from insert operation")
        except Exception as e:
            logger.error("Failed to create record", table=table, data=data, error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def update_record(self, table: str, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record in Supabase"""
        try:
            response = self.client.table(table).update(data).eq("id", record_id).execute()
            if response.data:
                return response.data[0]
            raise Exception("No data returned from update operation")
        except Exception as e:
            logger.error("Failed to update record", table=table, record_id=record_id, data=data, error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def delete_record(self, table: str, record_id: str) -> bool:
        """Delete a record from Supabase"""
        try:
            response = self.client.table(table).delete().eq("id", record_id).execute()
            return True
        except Exception as e:
            logger.error("Failed to delete record", table=table, record_id=record_id, error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def upsert_record(self, table: str, data: Dict[str, Any], 
                          on_conflict: str = "id") -> Dict[str, Any]:
        """Upsert (insert or update) a record in Supabase"""
        try:
            response = self.client.table(table).upsert(data, on_conflict=on_conflict).execute()
            if response.data:
                return response.data[0]
            raise Exception("No data returned from upsert operation")
        except Exception as e:
            logger.error("Failed to upsert record", table=table, data=data, error=str(e))
            raise
    
    async def search_records(self, table: str, search_term: str,
                           columns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search records in Supabase using text search"""
        try:
            query = self.client.table(table).select("*" if not columns else ",".join(columns))
            
            # Simple text search across common text fields
            # This is a basic implementation - you might want to use full-text search
            response = query.or_(f"name.ilike.%{search_term}%,email.ilike.%{search_term}%").execute()
            return response.data
        except Exception as e:
            logger.error("Failed to search records", table=table, search_term=search_term, error=str(e))
            raise
    
    async def get_table_schema(self, table: str) -> Dict[str, Any]:
        """Get table schema information from Supabase"""
        try:
            # This would require a custom RPC function or direct database access
            # For now, return a basic structure
            return {
                "table_name": table,
                "columns": []  # Would be populated by actual schema query
            }
        except Exception as e:
            logger.error("Failed to get table schema", table=table, error=str(e))
            raise
    
    async def execute_rpc(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a Supabase RPC function"""
        try:
            response = self.client.rpc(function_name, params or {}).execute()
            return response.data
        except Exception as e:
            logger.error("Failed to execute RPC", function_name=function_name, params=params, error=str(e))
            raise
