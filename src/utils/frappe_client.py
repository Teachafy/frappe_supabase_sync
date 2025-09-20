"""
Frappe API client for sync operations
"""
import httpx
from typing import Any, Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from ..config import settings
from .logger import get_logger

logger = get_logger(__name__)


class FrappeClient:
    """Client for interacting with Frappe API"""
    
    def __init__(self):
        self.base_url = settings.frappe_url.rstrip('/')
        self.api_key = settings.frappe_api_key
        self.api_secret = settings.frappe_api_secret
        self.headers = {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_document(self, doctype: str, name: str) -> Optional[Dict[str, Any]]:
        """Get a single document from Frappe"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/resource/{doctype}/{name}",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()["data"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("Document not found", doctype=doctype, name=name)
                return None
            raise
        except Exception as e:
            logger.error("Failed to get document", doctype=doctype, name=name, error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_documents(self, doctype: str, filters: Optional[Dict[str, Any]] = None, 
                          fields: Optional[List[str]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get multiple documents from Frappe"""
        try:
            params = {}
            if filters:
                import json
                params["filters"] = json.dumps(filters)
            if fields:
                import json
                params["fields"] = json.dumps(fields)
            params["limit_page_length"] = limit
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/resource/{doctype}",
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()["data"]
        except Exception as e:
            logger.error("Failed to get documents", doctype=doctype, error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def create_document(self, doctype: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document in Frappe"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/resource/{doctype}",
                    headers=self.headers,
                    json=data,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()["data"]
        except Exception as e:
            # Log response body for debugging
            try:
                if hasattr(e, 'response') and e.response:
                    response_body = e.response.text
                    logger.error("Failed to create document", doctype=doctype, data=data, error=str(e), response_body=response_body)
                else:
                    logger.error("Failed to create document", doctype=doctype, data=data, error=str(e))
            except Exception as e:
                logger.error("Failed to create document", doctype=doctype, data=data, error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def update_document(self, doctype: str, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing document in Frappe"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/api/resource/{doctype}/{name}",
                    headers=self.headers,
                    json=data,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()["data"]
        except Exception as e:
            logger.error("Failed to update document", doctype=doctype, name=name, data=data, error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def delete_document(self, doctype: str, name: str) -> bool:
        """Delete a document from Frappe"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/api/resource/{doctype}/{name}",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error("Failed to delete document", doctype=doctype, name=name, error=str(e))
            raise
    
    async def search_documents(self, doctype: str, search_term: str, 
                             fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search documents in Frappe"""
        try:
            params = {"q": search_term}
            if fields:
                params["fields"] = str(fields)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/resource/{doctype}",
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()["data"]
        except Exception as e:
            logger.error("Failed to search documents", doctype=doctype, search_term=search_term, error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def find_document_by_field(self, doctype: str, field: str, value: str) -> Optional[Dict[str, Any]]:
        """Find a document by a specific field value"""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "filters": f'[["{field}", "=", "{value}"]]',
                    "limit_page_length": 1
                }
                response = await client.get(
                    f"{self.base_url}/api/resource/{doctype}",
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()["data"]
                return data[0] if data else None
        except Exception as e:
            logger.error("Failed to find document by field", doctype=doctype, field=field, value=value, error=str(e))
            return None
    
    async def get_doctype_meta(self, doctype: str) -> Dict[str, Any]:
        """Get doctype metadata from Frappe"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/method/frappe.desk.form.load.getdoctype",
                    headers=self.headers,
                    params={"doctype": doctype},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()["message"]
        except Exception as e:
            logger.error("Failed to get doctype meta", doctype=doctype, error=str(e))
            raise
