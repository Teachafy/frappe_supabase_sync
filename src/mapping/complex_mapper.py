"""
Complex mapping engine for handling lookup relationships and ID transformations
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from ..utils.frappe_client import FrappeClient
from ..utils.supabase_client import SupabaseClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ComplexMapper:
    """Handles complex field mappings with lookups and transformations"""
    
    def __init__(self):
        self.frappe_client = FrappeClient()
        self.supabase_client = SupabaseClient()
        self.lookup_cache = {}
    
    async def map_complex_field(self, field_name: str, value: Any, 
                               mapping_config: Dict[str, Any], 
                               direction: str) -> Any:
        """Map a complex field with lookup logic"""
        try:
            if field_name not in mapping_config.get("complex_mappings", {}):
                return value
            
            complex_config = mapping_config["complex_mappings"][field_name]
            mapping_type = complex_config.get("type")
            
            if mapping_type == "lookup":
                return await self._handle_lookup_mapping(value, complex_config, direction)
            elif mapping_type == "prefix_transform":
                return await self._handle_prefix_transform(value, complex_config, direction)
            elif mapping_type == "email_priority":
                return await self._handle_email_priority(value, complex_config, direction)
            else:
                logger.warning(f"Unknown complex mapping type: {mapping_type}")
                return value
                
        except Exception as e:
            logger.error(f"Complex mapping failed for {field_name}", error=str(e))
            return value
    
    async def _handle_lookup_mapping(self, value: Any, config: Dict[str, Any], 
                                   direction: str) -> Any:
        """Handle lookup mapping between systems"""
        try:
            if direction == "frappe_to_supabase":
                # Convert Frappe ID to Supabase ID
                frappe_field = config.get("frappe_field", "name")
                supabase_field = config.get("supabase_field", "id")
                supabase_table = config.get("supabase_table")
                
                if not supabase_table:
                    return value
                
                # Check cache first
                cache_key = f"frappe_{value}_{supabase_table}"
                if cache_key in self.lookup_cache:
                    return self.lookup_cache[cache_key]
                
                # Lookup in Supabase
                records = await self.supabase_client.get_records(
                    supabase_table,
                    {frappe_field: value},
                    limit=1
                )
                
                if records:
                    result = records[0].get(supabase_field)
                    self.lookup_cache[cache_key] = result
                    return result
                else:
                    logger.warning(f"Lookup failed: {value} not found in {supabase_table}")
                    return value
                    
            else:  # supabase_to_frappe
                # Convert Supabase ID to Frappe ID
                supabase_field = config.get("supabase_field", "id")
                frappe_field = config.get("frappe_field", "name")
                frappe_doctype = config.get("frappe_doctype")
                
                if not frappe_doctype:
                    return value
                
                # Check cache first
                cache_key = f"supabase_{value}_{frappe_doctype}"
                if cache_key in self.lookup_cache:
                    return self.lookup_cache[cache_key]
                
                # Lookup in Frappe
                records = await self.frappe_client.get_documents(
                    frappe_doctype,
                    {frappe_field: value},
                    limit=1
                )
                
                if records:
                    result = records[0].get(frappe_field)
                    self.lookup_cache[cache_key] = result
                    return result
                else:
                    logger.warning(f"Lookup failed: {value} not found in {frappe_doctype}")
                    return value
                    
        except Exception as e:
            logger.error(f"Lookup mapping failed", error=str(e))
            return value
    
    async def _handle_prefix_transform(self, value: Any, config: Dict[str, Any], 
                                     direction: str) -> Any:
        """Handle prefix transformation (e.g., TASK-2025-0XXX)"""
        try:
            if direction == "frappe_to_supabase":
                # Convert Frappe prefixed ID to Supabase serial number
                prefix = config.get("prefix", "")
                if isinstance(value, str) and value.startswith(prefix):
                    # Extract the numeric part
                    numeric_part = value.replace(prefix, "").replace("-", "")
                    try:
                        return int(numeric_part)
                    except ValueError:
                        logger.warning(f"Could not extract numeric part from {value}")
                        return value
                return value
                
            else:  # supabase_to_frappe
                # Convert Supabase serial number to Frappe prefixed ID
                prefix = config.get("prefix", "")
                year = config.get("year", datetime.now().year)
                
                if isinstance(value, (int, str)):
                    try:
                        numeric_value = int(value)
                        # Format as TASK-2025-0XXX
                        formatted_id = f"{prefix}-{year}-{numeric_value:04d}"
                        return formatted_id
                    except ValueError:
                        logger.warning(f"Could not format {value} with prefix {prefix}")
                        return value
                return value
                
        except Exception as e:
            logger.error(f"Prefix transform failed", error=str(e))
            return value
    
    async def _handle_email_priority(self, value: Any, config: Dict[str, Any], 
                                   direction: str) -> Any:
        """Handle email field priority mapping"""
        try:
            if direction == "frappe_to_supabase":
                # Use the first available email from priority list
                email_fields = config.get("email_priority", ["personal_email"])
                
                if isinstance(value, dict):
                    for field in email_fields:
                        if field in value and value[field]:
                            return value[field]
                
                return value
                
            else:  # supabase_to_frappe
                # Map single email to multiple email fields
                email_fields = config.get("email_priority", ["personal_email"])
                
                if len(email_fields) == 1:
                    return {email_fields[0]: value}
                else:
                    # Distribute to multiple fields
                    result = {}
                    for field in email_fields:
                        result[field] = value
                    return result
                    
        except Exception as e:
            logger.error(f"Email priority mapping failed", error=str(e))
            return value
    
    async def map_task_project(self, project_value: Any, direction: str) -> Any:
        """Specialized mapping for Task-Project relationship"""
        try:
            if direction == "frappe_to_supabase":
                # Convert PROJ-0XX to numeric ID
                if isinstance(project_value, str) and project_value.startswith("PROJ-"):
                    # Extract numeric part
                    numeric_part = project_value.replace("PROJ-", "")
                    try:
                        return int(numeric_part)
                    except ValueError:
                        # Fallback: lookup by name
                        return await self._lookup_project_by_name(project_value, "supabase")
                return project_value
                
            else:  # supabase_to_frappe
                # Convert numeric ID to PROJ-0XX
                if isinstance(project_value, (int, str)):
                    try:
                        numeric_value = int(project_value)
                        return f"PROJ-{numeric_value:03d}"
                    except ValueError:
                        # Fallback: lookup by name
                        return await self._lookup_project_by_name(project_value, "frappe")
                return project_value
                
        except Exception as e:
            logger.error(f"Task project mapping failed", error=str(e))
            return project_value
    
    async def map_task_id(self, task_value: Any, direction: str) -> Any:
        """Specialized mapping for Task ID transformation"""
        try:
            if direction == "frappe_to_supabase":
                # Convert TASK-2025-0XXX to numeric ID
                if isinstance(task_value, str) and task_value.startswith("TASK-"):
                    # Extract numeric part
                    parts = task_value.split("-")
                    if len(parts) >= 3:
                        try:
                            return int(parts[2])
                        except ValueError:
                            pass
                return task_value
                
            else:  # supabase_to_frappe
                # Convert numeric ID to TASK-2025-0XXX
                if isinstance(task_value, (int, str)):
                    try:
                        numeric_value = int(task_value)
                        year = datetime.now().year
                        return f"TASK-{year}-{numeric_value:04d}"
                    except ValueError:
                        pass
                return task_value
                
        except Exception as e:
            logger.error(f"Task ID mapping failed", error=str(e))
            return task_value
    
    async def _lookup_project_by_name(self, name: str, target_system: str) -> Any:
        """Lookup project by name in target system"""
        try:
            if target_system == "supabase":
                records = await self.supabase_client.get_records(
                    "projects",
                    {"name": name},
                    limit=1
                )
                if records:
                    return records[0].get("id")
            else:  # frappe
                records = await self.frappe_client.get_documents(
                    "Project",
                    {"name": name},
                    limit=1
                )
                if records:
                    return records[0].get("name")
            
            return name
            
        except Exception as e:
            logger.error(f"Project lookup failed for {name}", error=str(e))
            return name
    
    def clear_cache(self):
        """Clear the lookup cache"""
        self.lookup_cache.clear()
        logger.info("Lookup cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.lookup_cache),
            "cache_keys": list(self.lookup_cache.keys())
        }
