"""
Field mapping and transformation system for Frappe-Supabase sync
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from ..utils.logger import get_logger
from .complex_mapper import ComplexMapper
from ..utils.phone_normalizer import (
    extract_phone_from_data,
    get_phone_lookup_fields,
    get_email_lookup_fields,
)

logger = get_logger(__name__)


class FieldMapper:
    """Handles field mapping and data transformation between Frappe and Supabase"""

    def __init__(self):
        self.complex_mapper = ComplexMapper()
        # No hardcoded default mappings - all mappings should come from configuration
        self.default_mappings = {}

    async def map_fields(
        self,
        data: Dict[str, Any],
        source_system: str,
        target_system: str,
        mapping: Dict[str, str],
    ) -> Dict[str, Any]:
        """Map fields from source system to target system"""
        try:
            # Validate direction
            valid_directions = ["frappe", "supabase"]
            if (
                source_system not in valid_directions
                or target_system not in valid_directions
            ):
                raise ValueError(
                    f"Invalid direction: {source_system} to {target_system}"
                )

            # Handle None data
            if data is None:
                return None

            # Make a copy of the data to prevent modifying the original
            import copy

            data = copy.deepcopy(data)
            mapped_data = {}

            # Get field mappings from configuration
            if source_system == "frappe" and target_system == "supabase":
                field_mappings = mapping.get("field_mappings", {})
                complex_mappings = mapping.get("complex_mappings", {})
            else:  # supabase to frappe
                field_mappings = mapping.get("reverse_mappings", {})
                complex_mappings = mapping.get("reverse_complex_mappings", {})

            sync_fields = mapping.get("sync_fields", [])

            # Filter out Frappe-specific fields that shouldn't be synced
            if source_system == "frappe":
                frappe_specific_fields = [
                    "_assign",
                    "__islocal",
                    "__unsaved",
                    "__user_tags",
                    "__comments",
                    "_user_tags",
                    "_comments",
                ]
                original_keys = list(data.keys())
                data = {
                    k: v for k, v in data.items() if k not in frappe_specific_fields
                }
                filtered_keys = list(data.keys())
                logger.info(
                    f"Filtered Frappe fields: {original_keys} -> {filtered_keys}"
                )

            # Apply complex mappings first (including email priority) to original data
            data = await self._apply_complex_mappings(
                data, complex_mappings, source_system, target_system
            )

            # Apply field mappings - only process explicitly mapped fields
            for source_field, target_field in field_mappings.items():
                if source_field in data:
                    # For organization_id, use the complex mapped value if available
                    if target_field == "organization_id" and "organization_id" in data:
                        mapped_data[target_field] = data["organization_id"]
                    # For company field, use the complex mapped value if available
                    elif target_field == "company" and "company" in data:
                        mapped_data[target_field] = data["company"]
                    # For status field that was processed by complex mapping, use the transformed value
                    elif (
                        source_field == "status"
                        and target_field == "_legacy_is_active"
                        and source_field in data
                    ):
                        # The complex mapping should have transformed status to a boolean
                        # Check if the complex mapping was applied
                        if source_field in data and isinstance(
                            data[source_field], bool
                        ):
                            mapped_data[target_field] = data[source_field]
                        else:
                            # Fallback to original value if complex mapping wasn't applied
                            mapped_data[target_field] = data[source_field]
                    # For company field that was processed by complex mapping, use the transformed value
                    elif (
                        source_field == "company"
                        and target_field == "organization_id"
                        and source_field in data
                    ):
                        # The complex mapping should have transformed company to organization_id
                        # Check if the complex mapping was applied
                        if (
                            source_field in data
                            and isinstance(data[source_field], str)
                            and len(data[source_field]) == 36
                        ):
                            # This looks like a UUID
                            mapped_data[target_field] = data[source_field]
                        else:
                            # Fallback to original value if complex mapping wasn't applied
                            mapped_data[target_field] = data[source_field]
                    elif (
                        target_field == "id"
                        and source_system == "frappe"
                        and target_system == "supabase"
                    ):
                        # Generate a UUID for Supabase id field
                        import uuid

                        mapped_data[target_field] = str(uuid.uuid4())
                    else:
                        # Skip fields that have complex mappings but failed (like project lookup)
                        if target_field in data and data[target_field] is None:
                            logger.warning(
                                f"Skipping field {target_field} due to failed complex mapping"
                            )
                            continue
                        # Use the complex mapped value if available, otherwise use the source field
                        if target_field in data:
                            mapped_data[target_field] = data[target_field]
                        else:
                            mapped_data[target_field] = data[source_field]
                elif target_field in data:
                    # Handle fields created by complex mappings (like 'name' from name_combination)
                    # But don't include 'name' field when syncing to Frappe as it should be auto-generated
                    if not (target_field == "name" and target_system == "frappe"):
                        # Skip fields that have complex mappings but failed
                        if data[target_field] is None:
                            logger.warning(
                                f"Skipping field {target_field} due to failed complex mapping"
                            )
                            continue
                        mapped_data[target_field] = data[target_field]

            # Only include fields that are explicitly mapped or created by complex mappings
            # This prevents unmapped fields from being included in the final data

            # No automatic field generation - all fields must be explicitly mapped in configuration

            # No default mappings - all field mappings must be explicitly defined in configuration

            # Only include fields that are explicitly mapped or created by complex mappings
            # Don't include unmapped fields to avoid schema mismatches

            # Only include fields that are explicitly mapped or created by complex mappings
            # Don't include all original fields to avoid schema mismatches

            # Apply email priority mapping
            mapped_data = await self._apply_email_priority_mapping(
                mapped_data, mapping, source_system, target_system
            )

            # Apply data transformations
            mapped_data = self._apply_transformations(
                mapped_data, source_system, target_system
            )

            # No automatic system metadata - all fields must be explicitly mapped in configuration

            # No hardcoded field generation - all fields must be explicitly mapped in configuration

            logger.debug(
                "Field mapping completed",
                source_system=source_system,
                target_system=target_system,
                original_fields=len(data),
                mapped_fields=len(mapped_data),
            )

            # Debug logging
            logger.info(
                f"Final mapped data for {source_system} -> {target_system}: {mapped_data}"
            )

            return mapped_data

        except Exception as e:
            logger.error(
                "Field mapping failed",
                error=str(e),
                source_system=source_system,
                target_system=target_system,
            )
            raise

    def _apply_transformations(
        self, data: Dict[str, Any], source_system: str, target_system: str
    ) -> Dict[str, Any]:
        """Apply data transformations based on system requirements"""
        transformed_data = data.copy()

        # Transform timestamps
        transformed_data = self._transform_timestamps(
            transformed_data, source_system, target_system
        )

        # Transform boolean fields
        transformed_data = self._transform_booleans(
            transformed_data, source_system, target_system
        )

        # Transform null values
        transformed_data = self._transform_null_values(transformed_data, target_system)

        # Transform field names to match target system conventions
        transformed_data = self._transform_field_names(transformed_data, target_system)

        return transformed_data

    def _transform_timestamps(
        self, data: Dict[str, Any], source_system: str, target_system: str
    ) -> Dict[str, Any]:
        """Transform timestamp fields between systems"""
        timestamp_fields = ["created_at", "updated_at", "creation", "modified"]

        for field in timestamp_fields:
            if field in data and data[field]:
                try:
                    # Parse and reformat timestamp
                    if isinstance(data[field], str):
                        # Parse ISO format timestamp
                        dt = datetime.fromisoformat(data[field].replace("Z", "+00:00"))
                    else:
                        dt = data[field]

                    # Format for target system
                    if target_system == "supabase":
                        data[field] = dt.isoformat()
                    elif target_system == "frappe":
                        data[field] = dt.strftime("%Y-%m-%d %H:%M:%S")

                except Exception as e:
                    logger.warning(f"Failed to transform timestamp field {field}: {e}")

        return data

    def _transform_booleans(
        self, data: Dict[str, Any], source_system: str, target_system: str
    ) -> Dict[str, Any]:
        """Transform boolean fields between systems"""
        boolean_fields = ["disabled", "enabled", "active", "inactive", "verified"]

        for field in boolean_fields:
            if field in data:
                value = data[field]

                # Convert to boolean if needed
                if isinstance(value, str):
                    if value.lower() in ["true", "1", "yes", "on", "active"]:
                        data[field] = True
                    elif value.lower() in ["false", "0", "no", "off", "inactive"]:
                        data[field] = False
                elif isinstance(value, int):
                    data[field] = bool(value)

        return data

    def _transform_null_values(
        self, data: Dict[str, Any], target_system: str
    ) -> Dict[str, Any]:
        """Transform null values based on target system requirements"""
        for key, value in data.items():
            if value is None or value == "":
                if target_system == "supabase":
                    # Supabase prefers None for null values
                    data[key] = None
                elif target_system == "frappe":
                    # Frappe prefers empty string for null values
                    data[key] = ""

        return data

    def _transform_field_names(
        self, data: Dict[str, Any], target_system: str
    ) -> Dict[str, Any]:
        """Transform field names to match target system conventions"""
        if target_system == "supabase":
            # Convert to snake_case
            transformed = {}
            for key, value in data.items():
                snake_key = self._to_snake_case(key)
                transformed[snake_key] = value
            return transformed
        elif target_system == "frappe":
            # Convert to snake_case for Frappe
            transformed = {}
            for key, value in data.items():
                snake_key = self._to_snake_case(key)
                transformed[snake_key] = value
            return transformed

        return data

    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case"""
        import re

        # Insert an underscore before any uppercase letter that follows a lowercase letter
        s1 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", text)
        # Convert to lowercase
        return s1.lower()

    def _add_system_metadata(
        self, data: Dict[str, Any], target_system: str
    ) -> Dict[str, Any]:
        """Add system-specific metadata"""
        now = datetime.utcnow()

        if target_system == "supabase":
            data["updated_at"] = now.isoformat()
            if "created_at" not in data:
                data["created_at"] = now.isoformat()
        elif target_system == "frappe":
            data["modified"] = now.strftime("%Y-%m-%d %H:%M:%S")
            if "creation" not in data:
                data["creation"] = now.strftime("%Y-%m-%d %H:%M:%S")

        return data

    async def _apply_email_priority_mapping(
        self,
        data: Dict[str, Any],
        mapping: Dict[str, str],
        source_system: str,
        target_system: str,
    ) -> Dict[str, Any]:
        """Apply email priority mapping for employee data"""
        try:
            if source_system == "supabase" and target_system == "frappe":
                # Map single email to personal_email field
                if "email" in data and "personal_email" not in data:
                    data["personal_email"] = data["email"]
                return data
            elif source_system == "frappe" and target_system == "supabase":
                # Use email priority to select the best email
                # Default priority if not found in complex mappings
                email_priority = [
                    "personal_email",
                    "company_email",
                    "preferred_contact_email",
                ]

                for email_field in email_priority:
                    if email_field in data and data[email_field]:
                        data["email"] = data[email_field]
                        break
                return data

            return data

        except Exception as e:
            logger.error("Email priority mapping failed", error=str(e))
            return data

    async def _apply_complex_mappings(
        self,
        data: Dict[str, Any],
        complex_mappings: Dict[str, Any],
        source_system: str,
        target_system: str,
    ) -> Dict[str, Any]:
        """Apply complex mappings with lookup logic"""
        try:
            # Make a copy of the data to prevent modifying the original
            import copy

            data = copy.deepcopy(data)

            # Handle email priority mapping specially
            if (
                "email" in complex_mappings
                and complex_mappings["email"].get("type") == "email_priority"
            ):
                if source_system == "frappe" and target_system == "supabase":
                    email_priority = complex_mappings["email"].get(
                        "email_priority", ["personal_email", "company_email"]
                    )
                    for email_field in email_priority:
                        if email_field in data and data[email_field]:
                            data["email"] = data[email_field]
                            break

            # Handle name combination mapping specially
            if (
                "name" in complex_mappings
                and complex_mappings["name"].get("type") == "name_combination"
            ):
                if source_system == "frappe" and target_system == "supabase":
                    first_name = data.get("first_name", "")
                    last_name = data.get("last_name", "")
                    data["name"] = f"{first_name} {last_name}".strip()
                    # Don't remove the individual name fields yet - let the field mapping handle them
                elif source_system == "supabase" and target_system == "frappe":
                    # Split combined name back to first_name and last_name
                    full_name = data.get("name", "")
                    name_parts = full_name.split(" ", 1)
                    data["first_name"] = name_parts[0] if name_parts else ""
                    data["last_name"] = name_parts[1] if len(name_parts) > 1 else ""
                    logger.debug(
                        f"Split name '{full_name}' into first_name='{data['first_name']}' and last_name='{data['last_name']}'"
                    )
                    # Remove the combined name field
                    if "name" in data:
                        del data["name"]

            # Handle reverse name combination mapping specially
            logger.debug(
                f"Checking reverse name combination: first_name in complex_mappings: {'first_name' in complex_mappings}"
            )
            if "first_name" in complex_mappings:
                logger.debug(
                    f"first_name complex mapping: {complex_mappings['first_name']}"
                )
            if (
                "first_name" in complex_mappings
                and complex_mappings["first_name"].get("type")
                == "reverse_name_combination"
            ):
                logger.debug(
                    f"Applying reverse name combination for {source_system} -> {target_system}"
                )
                if source_system == "supabase" and target_system == "frappe":
                    # Split combined name back to first_name and last_name
                    full_name = data.get("name", "")
                    name_parts = full_name.split(" ", 1)
                    data["first_name"] = name_parts[0] if name_parts else ""
                    data["last_name"] = name_parts[1] if len(name_parts) > 1 else ""
                    logger.debug(
                        f"Split name '{full_name}' into first_name='{data['first_name']}' and last_name='{data['last_name']}'"
                    )
                    # Remove the combined name field
                    if "name" in data:
                        del data["name"]

            # Handle other complex mappings
            for field_name, complex_config in complex_mappings.items():
                # Skip reverse_name_combination as it's handled in the special case section above
                if complex_config.get("type") == "reverse_name_combination":
                    continue
                # For organization_id mapping, apply to the organization_id field
                if field_name == "organization_id" and "organization_id" in data:
                    logger.debug(
                        f"Applying organization_id complex mapping: {data['organization_id']} -> {complex_config}"
                    )
                    mapped_value = await self.complex_mapper.handle_complex_mapping(
                        data["organization_id"],
                        complex_config,
                        f"{source_system}_to_{target_system}",
                        source_system,
                        target_system,
                    )
                    logger.debug(f"Complex mapping result: {mapped_value}")
                    data["company"] = mapped_value
                elif (
                    field_name == "start_date"
                    and complex_config.get("type") == "date_format_conversion"
                ):
                    # Handle date format conversion for start_date
                    if field_name in data:
                        mapped_value = await self.complex_mapper.handle_complex_mapping(
                            data[field_name],
                            complex_config,
                            f"{source_system}_to_{target_system}",
                            source_system,
                            target_system,
                        )
                        data[field_name] = mapped_value
                elif (
                    field_name == "end_date"
                    and complex_config.get("type") == "date_format_conversion"
                ):
                    # Handle date format conversion for end_date
                    if field_name in data:
                        mapped_value = await self.complex_mapper.handle_complex_mapping(
                            data[field_name],
                            complex_config,
                            f"{source_system}_to_{target_system}",
                            source_system,
                            target_system,
                        )
                        data[field_name] = mapped_value
                elif (
                    field_name == "act_start_date"
                    and complex_config.get("type") == "date_fallback"
                ):
                    # Handle date fallback for act_start_date
                    mapped_value = (
                        await self.complex_mapper._handle_date_fallback_mapping(
                            data, complex_config, source_system, target_system
                        )
                    )
                    if mapped_value is not None:
                        data[field_name] = mapped_value
                elif (
                    field_name == "act_end_date"
                    and complex_config.get("type") == "date_fallback"
                ):
                    # Handle date fallback for act_end_date
                    mapped_value = (
                        await self.complex_mapper._handle_date_fallback_mapping(
                            data, complex_config, source_system, target_system
                        )
                    )
                    if mapped_value is not None:
                        data[field_name] = mapped_value
                elif (
                    field_name == "organization_id"
                    and complex_config.get("type") == "default_value"
                ):
                    # Handle default value for organization_id
                    mapped_value = (
                        await self.complex_mapper._handle_default_value_mapping(
                            data, complex_config, source_system, target_system
                        )
                    )
                    if mapped_value is not None:
                        data[field_name] = mapped_value
                elif (
                    field_name == "gender"
                    and complex_config.get("type") == "default_value"
                ):
                    # Handle default value for gender
                    mapped_value = (
                        await self.complex_mapper._handle_default_value_mapping(
                            data, complex_config, source_system, target_system
                        )
                    )
                    if mapped_value is not None:
                        data[field_name] = mapped_value
                elif (
                    field_name == "date_of_birth"
                    and complex_config.get("type") == "default_value"
                ):
                    # Handle default value for date_of_birth
                    mapped_value = (
                        await self.complex_mapper._handle_default_value_mapping(
                            data, complex_config, source_system, target_system
                        )
                    )
                    if mapped_value is not None:
                        data[field_name] = mapped_value
                elif (
                    field_name == "date_of_joining"
                    and complex_config.get("type") == "default_value"
                ):
                    # Handle default value for date_of_joining
                    mapped_value = (
                        await self.complex_mapper._handle_default_value_mapping(
                            data, complex_config, source_system, target_system
                        )
                    )
                    if mapped_value is not None:
                        data[field_name] = mapped_value
                elif (
                    field_name == "start_date"
                    and complex_config.get("type") == "date_format_conversion"
                ):
                    # Handle date format conversion for start_date (Supabase -> Frappe)
                    mapped_value = (
                        await self.complex_mapper._handle_date_format_conversion(
                            data.get(field_name),
                            complex_config,
                            source_system,
                            target_system,
                        )
                    )
                    if mapped_value is not None:
                        data[field_name] = mapped_value
                elif (
                    field_name == "end_date"
                    and complex_config.get("type") == "date_format_conversion"
                ):
                    # Handle date format conversion for end_date (Supabase -> Frappe)
                    mapped_value = (
                        await self.complex_mapper._handle_date_format_conversion(
                            data.get(field_name),
                            complex_config,
                            source_system,
                            target_system,
                        )
                    )
                    if mapped_value is not None:
                        data[field_name] = mapped_value
                elif (
                    field_name in data
                    and complex_config.get("type") != "email_priority"
                ):
                    mapped_value = await self.complex_mapper.handle_complex_mapping(
                        data[field_name],
                        complex_config,
                        f"{source_system}_to_{target_system}",
                    )
                    data[field_name] = mapped_value

            return data

        except Exception as e:
            logger.error("Complex mapping failed", error=str(e))
            return data

    def get_primary_identifier(
        self, data: dict, source_system: str, target_system: str
    ) -> Optional[tuple]:
        """
        Get the primary identifier for record lookup (phone, email, or task subject)

        Returns:
            Tuple of (identifier_type, identifier_value) or None
            identifier_type: 'phone', 'email', or 'task_subject'
            identifier_value: normalized identifier
        """
        try:
            # For Tasks: use subject/task_name + description for lookup
            if self._is_task_record(data, source_system, target_system):
                subject = (
                    data.get("subject") or data.get("task_name") or data.get("name")
                )
                description = data.get("description") or data.get("page_content") or ""

                if subject:
                    # Use subject + first 50 chars of description for better uniqueness
                    desc_snippet = (
                        description[:50].replace("\n", " ").strip()
                        if description
                        else ""
                    )
                    identifier = subject
                    if desc_snippet:
                        identifier += f"|{desc_snippet}"
                    return ("task_subject", identifier)

            # For Employee/Users: try phone number first
            phone_fields = get_phone_lookup_fields(source_system, target_system)
            phone = extract_phone_from_data(data, phone_fields)
            if phone:
                return ("phone", phone)

            # Fallback to email
            email_fields = get_email_lookup_fields(source_system, target_system)
            for field in email_fields:
                if field in data and data[field]:
                    return ("email", data[field])

        except Exception as e:
            logger.error("Error getting primary identifier", error=str(e))

        return None

    def _is_task_record(
        self, data: dict, source_system: str, target_system: str
    ) -> bool:
        """Check if this is a Task record based on available fields"""
        task_fields = [
            "subject",
            "task_name",
            "description",
            "page_content",
            "progress",
            "is_milestone",
        ]
        return any(field in data for field in task_fields)

    def create_field_mapping(
        self, doctype: str, table: str, field_mappings: Dict[str, str]
    ) -> Dict[str, str]:
        """Create a field mapping configuration"""
        return {
            "frappe_doctype": doctype,
            "supabase_table": table,
            "field_mappings": field_mappings,
            "sync_fields": list(field_mappings.keys()),
        }

    def validate_mapping(self, mapping: Dict[str, str]) -> List[str]:
        """Validate a field mapping configuration"""
        errors = []

        required_fields = ["frappe_doctype", "supabase_table", "field_mappings"]
        for field in required_fields:
            if field not in mapping:
                errors.append(f"Missing required field: {field}")

        if "field_mappings" in mapping and not isinstance(
            mapping["field_mappings"], dict
        ):
            errors.append("field_mappings must be a dictionary")

        return errors
