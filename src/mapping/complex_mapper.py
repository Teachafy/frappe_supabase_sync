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

    async def handle_complex_mapping(
        self,
        value: Any,
        config: Dict[str, Any],
        direction: str,
        source_system: str = None,
        target_system: str = None,
    ) -> Any:
        """Handle complex mapping for a single field"""
        try:
            mapping_type = config.get("type")

            if mapping_type == "array_to_uuid_array":
                return await self._handle_array_mapping(value, config, direction)
            elif mapping_type == "is_milestone_to_needs_submission":
                return await self._handle_boolean_mapping(value, config, direction)
            elif mapping_type == "needs_submission_to_is_milestone":
                return await self._handle_boolean_mapping(value, config, direction)
            elif mapping_type == "email_priority":
                return await self._handle_email_priority(value, config, direction)
            elif mapping_type == "status_mapping":
                return await self._handle_boolean_mapping(value, config, direction)
            elif mapping_type == "name_combination":
                return await self._handle_name_combination(value, config, direction)
            elif mapping_type == "lookup":
                return await self._handle_lookup_mapping(value, config, direction)
            elif mapping_type == "company_to_org_mapping":
                return await self._handle_company_to_org_mapping(
                    value, config, direction
                )
            elif mapping_type == "string_to_int":
                return await self._handle_string_to_int_mapping(
                    value, config, direction
                )
            elif mapping_type == "reverse_name_combination":
                return await self._handle_reverse_name_combination(
                    value, config, direction
                )
            elif mapping_type == "project_lookup":
                return await self._handle_project_lookup(value, config, direction)
            elif mapping_type == "date_fallback":
                return await self._handle_date_fallback_mapping(
                    value, config, source_system, target_system
                )
            elif mapping_type == "default_value":
                return await self._handle_default_value_mapping(
                    value, config, source_system, target_system
                )
            elif mapping_type == "date_format_conversion":
                return await self._handle_date_format_conversion(
                    value, config, source_system, target_system
                )
            else:
                logger.warning(f"Unknown complex mapping type: {mapping_type}")
                return value
        except Exception as e:
            logger.error(f"Complex mapping failed", error=str(e))
            return value

    async def map_complex_field(
        self,
        field_name: str,
        value: Any,
        mapping_config: Dict[str, Any],
        direction: str,
    ) -> Any:
        """Map a complex field with lookup logic"""
        try:
            if field_name not in mapping_config.get("complex_mappings", {}):
                return value

            complex_config = mapping_config["complex_mappings"][field_name]
            mapping_type = complex_config.get("type")

            if mapping_type == "lookup":
                return await self._handle_lookup_mapping(
                    value, complex_config, direction
                )
            elif mapping_type == "prefix_transform":
                return await self._handle_prefix_transform(
                    value, complex_config, direction
                )
            elif mapping_type == "email_priority":
                return await self._handle_email_priority(
                    value, complex_config, direction
                )
            else:
                logger.warning(f"Unknown complex mapping type: {mapping_type}")
                return value

        except Exception as e:
            logger.error(f"Complex mapping failed for {field_name}", error=str(e))
            return value

    async def _handle_lookup_mapping(
        self, value: Any, config: Dict[str, Any], direction: str
    ) -> Any:
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
                    supabase_table, {frappe_field: value}, limit=1
                )

                if records:
                    result = records[0].get(supabase_field)
                    self.lookup_cache[cache_key] = result
                    return result
                else:
                    logger.warning(
                        f"Lookup failed: {value} not found in {supabase_table}"
                    )
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
                    frappe_doctype, {frappe_field: value}, limit=1
                )

                if records:
                    result = records[0].get(frappe_field)
                    self.lookup_cache[cache_key] = result
                    return result
                else:
                    logger.warning(
                        f"Lookup failed: {value} not found in {frappe_doctype}"
                    )
                    return value

        except Exception as e:
            logger.error(f"Lookup mapping failed", error=str(e))
            return value

    async def _handle_prefix_transform(
        self, value: Any, config: Dict[str, Any], direction: str
    ) -> Any:
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

    async def _handle_email_priority(
        self, value: Any, config: Dict[str, Any], direction: str
    ) -> Any:
        """Handle email field priority mapping"""
        try:
            if direction == "frappe_to_supabase":
                # Use the first available email from priority list
                email_fields = config.get(
                    "email_priority",
                    ["personal_email", "company_email", "preferred_contact_email"],
                )

                if isinstance(value, dict):
                    for field in email_fields:
                        if field in value and value[field]:
                            return value[field]

                # If no email found in priority fields, return None
                return None

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

    async def _handle_company_to_org_mapping(
        self, value: Any, config: Dict[str, Any], direction: str
    ) -> Any:
        """Handle company name to organization ID mapping"""
        try:
            mappings = config.get("mappings", {})

            if direction == "frappe_to_supabase":
                # Map Frappe company name to Supabase organization ID
                return mappings.get(value, value)
            else:  # supabase_to_frappe
                # For reverse mapping, the config already contains UUID -> company name mapping
                # So we can use it directly
                return mappings.get(value, value)
        except Exception as e:
            logger.error(f"Company to org mapping failed", error=str(e))
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
                        return await self._lookup_project_by_name(
                            project_value, "supabase"
                        )
                return project_value

            else:  # supabase_to_frappe
                # Convert numeric ID to PROJ-0XX
                if isinstance(project_value, (int, str)):
                    try:
                        numeric_value = int(project_value)
                        return f"PROJ-{numeric_value:03d}"
                    except ValueError:
                        # Fallback: lookup by name
                        return await self._lookup_project_by_name(
                            project_value, "frappe"
                        )
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
                    "projects", {"name": name}, limit=1
                )
                if records:
                    return records[0].get("id")
            else:  # frappe
                records = await self.frappe_client.get_documents(
                    "Project", {"name": name}, limit=1
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
            "cache_keys": list(self.lookup_cache.keys()),
        }

    async def _handle_array_mapping(
        self, value: Any, config: Dict[str, Any], direction: str
    ) -> Any:
        """Handle array field mapping"""
        try:
            # Handle string representation of list
            if isinstance(value, str):
                try:
                    import ast

                    value = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    # If it's not a valid Python literal, return as is
                    return value

            if not isinstance(value, list):
                return value

            if direction == "frappe_to_supabase":
                # Convert array of emails to array of UUIDs
                if config.get("type") == "array_to_uuid_array":
                    # For now, return the original array (would need lookup for UUIDs)
                    return value
                return value
            else:  # supabase_to_frappe
                # Convert array of UUIDs to array of emails
                if config.get("type") == "uuid_array_to_array":
                    # For now, return the original array (would need lookup for emails)
                    return value
                return value

        except Exception as e:
            logger.error(f"Array mapping failed", error=str(e))
            return value

    async def _handle_boolean_mapping(
        self, value: Any, config: Dict[str, Any], direction: str
    ) -> Any:
        """Handle boolean field mapping"""
        try:
            if direction == "frappe_to_supabase":
                # Convert Frappe boolean to Supabase boolean
                if config.get("type") == "is_milestone_to_needs_submission":
                    return bool(value) if value is not None else False
                elif config.get("type") == "status_mapping":
                    # Convert status string to boolean
                    active_status = config.get("active_status", "Active")
                    inactive_status = config.get("inactive_status", "Inactive")
                    return value == active_status

                # Handle string values
                if isinstance(value, str):
                    if value.lower() in ["true", "1", "yes", "on", "active"]:
                        return True
                    elif value.lower() in ["false", "0", "no", "off", "inactive"]:
                        return False

                return bool(value) if value is not None else False
            else:  # supabase_to_frappe
                # Convert Supabase boolean to Frappe boolean
                if config.get("type") == "needs_submission_to_is_milestone":
                    return 1 if value else 0
                elif config.get("type") == "status_mapping":
                    # Convert boolean to status string
                    active_status = config.get("active_status", "Active")
                    inactive_status = config.get("inactive_status", "Inactive")
                    return active_status if value else inactive_status
                return 1 if value else 0

        except Exception as e:
            logger.error(f"Boolean mapping failed", error=str(e))
            return value

    async def _handle_datetime_mapping(
        self, value: Any, config: Dict[str, Any], direction: str
    ) -> Any:
        """Handle datetime field mapping"""
        try:
            if not value:
                return value

            if direction == "frappe_to_supabase":
                # Convert Frappe datetime to Supabase format
                if isinstance(value, str):
                    # Parse and reformat if needed
                    return value
                return value
            else:  # supabase_to_frappe
                # Convert Supabase datetime to Frappe format
                if isinstance(value, str):
                    # Parse and reformat if needed
                    return value
                return value

        except Exception as e:
            logger.error(f"Datetime mapping failed", error=str(e))
            return value

    async def _handle_complex_mapping(
        self,
        field_name: str,
        value: Any,
        mapping_config: Dict[str, Any],
        direction: str,
    ) -> Any:
        """Handle complex mapping with error handling"""
        try:
            return await self.map_complex_field(
                field_name, value, mapping_config, direction
            )
        except Exception as e:
            logger.error(f"Complex mapping failed for {field_name}", error=str(e))
            return value

    async def apply_complex_mappings(
        self, data: Dict[str, Any], mapping_config: Dict[str, Any], direction: str
    ) -> Dict[str, Any]:
        """Apply all complex mappings to data"""
        try:
            if not data or not mapping_config.get("complex_mappings"):
                return data

            result = data.copy()
            complex_mappings = mapping_config["complex_mappings"]

            for field_name, complex_config in complex_mappings.items():
                if field_name in result:
                    mapped_value = await self._handle_complex_mapping(
                        field_name, result[field_name], mapping_config, direction
                    )
                    result[field_name] = mapped_value

            return result

        except Exception as e:
            logger.error(f"Apply complex mappings failed", error=str(e))
            return data

    async def _handle_name_combination(
        self, value: Any, config: Dict[str, Any], direction: str
    ) -> Any:
        """Handle name combination mapping (first_name + last_name)"""
        try:
            if direction == "frappe_to_supabase":
                # Combine first_name and last_name for Supabase name field
                first_name = config.get("first_name_field", "first_name")
                last_name = config.get("last_name_field", "last_name")

                # This would be called with the full data object, not just the name value
                if isinstance(value, dict):
                    first = value.get(first_name, "")
                    last = value.get(last_name, "")
                    return f"{first} {last}".strip()
                return value
            else:  # supabase_to_frappe
                # Split Supabase name back to first_name and last_name
                if isinstance(value, str) and value:
                    parts = value.split(" ", 1)
                    return {
                        "first_name": parts[0],
                        "last_name": parts[1] if len(parts) > 1 else "",
                    }
                return value

        except Exception as e:
            logger.error(f"Name combination mapping failed", error=str(e))
            return value

    async def _handle_string_to_int_mapping(
        self, value: Any, config: Dict[str, Any], direction: str
    ) -> Any:
        """Handle string to integer mapping (e.g., PROJ-0001 -> 1)"""
        try:
            if not value:
                return None

            if direction == "frappe_to_supabase":
                # Convert Frappe project string to integer
                if isinstance(value, str) and value.startswith("PROJ-"):
                    # Extract number from PROJ-0001 format
                    try:
                        return int(value.split("-")[1])
                    except (IndexError, ValueError):
                        logger.warning(
                            f"Could not convert project string {value} to integer"
                        )
                        return None
                return value
            else:  # supabase_to_frappe
                # Convert Supabase integer to Frappe project string
                if isinstance(value, int):
                    return f"PROJ-{value:04d}"
                return value

        except Exception as e:
            logger.error(f"String to int mapping failed", error=str(e))
            return value

    async def _handle_reverse_name_combination(
        self, value: Any, config: Dict[str, Any], direction: str
    ) -> Any:
        """Handle reverse name combination (e.g., "John Doe" -> {"first_name": "John", "last_name": "Doe"})"""
        try:
            if not value:
                return None

            if direction == "supabase_to_frappe":
                # Split Supabase name into first_name and last_name
                if isinstance(value, str) and value:
                    parts = value.split(" ", 1)
                    return {
                        "first_name": parts[0],
                        "last_name": parts[1] if len(parts) > 1 else "",
                    }
                return value
            else:  # frappe_to_supabase
                # This shouldn't be called in this direction
                return value

        except Exception as e:
            logger.error(f"Reverse name combination mapping failed", error=str(e))
            return value

    async def _handle_project_lookup(
        self, value: Any, config: Dict[str, Any], direction: str
    ) -> Any:
        """Handle project lookup between Frappe and Supabase"""
        try:
            if not value:
                return None

            if direction == "frappe_to_supabase":
                # Convert Frappe project name to Supabase project ID
                frappe_field = config.get("frappe_field", "name")
                supabase_field = config.get("supabase_field", "id")
                supabase_table = config.get("supabase_table", "projects")

                if not supabase_table:
                    return value

                # Check cache first
                cache_key = f"frappe_project_{value}_{supabase_table}"
                if cache_key in self.lookup_cache:
                    return self.lookup_cache[cache_key]

                # Lookup in Supabase projects table
                records = await self.supabase_client.get_records(
                    supabase_table, {frappe_field: value}, limit=1
                )

                if records:
                    result = records[0].get(supabase_field)
                    self.lookup_cache[cache_key] = result
                    return result
                else:
                    logger.warning(
                        f"Project lookup failed: {value} not found in {supabase_table}"
                    )
                    # Return None instead of the original value to indicate lookup failed
                    return None

            else:  # supabase_to_frappe
                # Convert Supabase project ID to Frappe project name
                supabase_field = config.get("supabase_field", "id")
                frappe_field = config.get("frappe_field", "name")
                frappe_doctype = "Project"

                if not frappe_doctype:
                    return value

                # Check cache first
                cache_key = f"supabase_project_{value}_{frappe_doctype}"
                if cache_key in self.lookup_cache:
                    return self.lookup_cache[cache_key]

                # Lookup in Frappe Project doctype
                records = await self.frappe_client.get_records(
                    frappe_doctype, {supabase_field: value}, limit=1
                )

                if records:
                    result = records[0].get(frappe_field)
                    self.lookup_cache[cache_key] = result
                    return result
                else:
                    logger.warning(
                        f"Project lookup failed: {value} not found in {frappe_doctype}"
                    )
                    return value

        except Exception as e:
            logger.error(f"Project lookup mapping failed", error=str(e))
            return value

    async def _handle_date_fallback_mapping(
        self,
        data: Dict[str, Any],
        mapping: Dict[str, Any],
        source_system: str,
        target_system: str,
    ) -> Any:
        """Handle date fallback mapping - use primary field if available, otherwise fallback field"""
        try:
            primary_field = mapping.get("primary_field")
            fallback_field = mapping.get("fallback_field")

            if not primary_field or not fallback_field:
                logger.warning(
                    "Date fallback mapping missing primary_field or fallback_field"
                )
                return None

            # Try primary field first
            if primary_field in data and data[primary_field] is not None:
                return data[primary_field]

            # Try fallback field if primary is not available
            if fallback_field in data and data[fallback_field] is not None:
                logger.info(
                    f"Using fallback field {fallback_field} for {primary_field}"
                )
                return data[fallback_field]

            # Both fields are None or not present
            logger.info(
                f"Both {primary_field} and {fallback_field} are None or not present"
            )
            return None

        except Exception as e:
            logger.error(f"Date fallback mapping failed", error=str(e))
            return None

    async def _handle_default_value_mapping(
        self,
        data: Dict[str, Any],
        mapping: Dict[str, Any],
        source_system: str,
        target_system: str,
    ) -> Any:
        """Handle default value mapping - return a default value for a field"""
        try:
            default_value = mapping.get("value")
            if default_value is not None:
                logger.info(f"Using default value for organization_id: {default_value}")
                return default_value
            else:
                logger.warning("Default value mapping missing value")
                return None

        except Exception as e:
            logger.error(f"Default value mapping failed", error=str(e))
            return None

    async def _handle_date_format_conversion(
        self, value: Any, config: Dict[str, Any], source_system: str, target_system: str
    ) -> Any:
        """Handle date format conversion - convert ISO datetime to date string"""
        try:
            logger.debug(
                f"Date format conversion called with value: {value}, config: {config}"
            )
            if not value:
                return value

            input_format = config.get("input_format")
            output_format = config.get("output_format")

            if input_format == "iso_datetime" and output_format == "date_string":
                # Convert ISO datetime string to date string
                if isinstance(value, str) and "T" in value:
                    # Extract just the date part (before the 'T')
                    date_part = value.split("T")[0]
                    logger.info(f"Converted ISO datetime {value} to date {date_part}")
                    return date_part
                else:
                    logger.warning(f"Expected ISO datetime string, got: {value}")
                    return value
            else:
                logger.warning(
                    f"Unsupported date format conversion: {input_format} -> {output_format}"
                )
                return value

        except Exception as e:
            logger.error(f"Date format conversion failed", error=str(e))
            return value
