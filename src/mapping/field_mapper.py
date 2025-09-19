"""
Field mapping and transformation system for Frappe-Supabase sync
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from ..utils.logger import get_logger
from .complex_mapper import ComplexMapper

logger = get_logger(__name__)


class FieldMapper:
    """Handles field mapping and data transformation between Frappe and Supabase"""
    
    def __init__(self):
        self.complex_mapper = ComplexMapper()
        self.default_mappings = {
            "frappe_to_supabase": {
                "name": "id",
                "creation": "created_at",
                "modified": "updated_at",
                "owner": "created_by",
                "modified_by": "updated_by"
            },
            "supabase_to_frappe": {
                "id": "name",
                "created_at": "creation",
                "updated_at": "modified",
                "created_by": "owner",
                "updated_by": "modified_by"
            }
        }
    
    async def map_fields(self, data: Dict[str, Any], source_system: str, target_system: str, 
                   mapping_config: Dict[str, str]) -> Dict[str, Any]:
        """Map fields from source system to target system"""
        try:
            mapped_data = {}
            
            # Get field mappings from configuration
            field_mappings = mapping_config.get("field_mappings", {})
            sync_fields = mapping_config.get("sync_fields", [])
            
            # Apply field mappings
            for source_field, target_field in field_mappings.items():
                if source_field in data:
                    mapped_data[target_field] = data[source_field]
            
            # Apply default mappings for unmapped fields
            default_mapping_key = f"{source_system}_to_{target_system}"
            if default_mapping_key in self.default_mappings:
                for source_field, target_field in self.default_mappings[default_mapping_key].items():
                    if source_field in data and target_field not in mapped_data:
                        mapped_data[target_field] = data[source_field]
            
            # Include sync fields that don't have explicit mappings
            for field in sync_fields:
                if field in data and field not in mapped_data:
                    mapped_data[field] = data[field]
            
            # Apply complex mappings
            mapped_data = await self._apply_complex_mappings(mapped_data, mapping_config, source_system, target_system)
            
            # Apply data transformations
            mapped_data = self._apply_transformations(mapped_data, source_system, target_system)
            
            # Add system metadata
            mapped_data = self._add_system_metadata(mapped_data, target_system)
            
            logger.debug(
                "Field mapping completed",
                source_system=source_system,
                target_system=target_system,
                original_fields=len(data),
                mapped_fields=len(mapped_data)
            )
            
            return mapped_data
            
        except Exception as e:
            logger.error("Field mapping failed", error=str(e), source_system=source_system, target_system=target_system)
            raise
    
    def _apply_transformations(self, data: Dict[str, Any], source_system: str, target_system: str) -> Dict[str, Any]:
        """Apply data transformations based on system requirements"""
        transformed_data = data.copy()
        
        # Transform timestamps
        transformed_data = self._transform_timestamps(transformed_data, source_system, target_system)
        
        # Transform boolean fields
        transformed_data = self._transform_booleans(transformed_data, source_system, target_system)
        
        # Transform null values
        transformed_data = self._transform_null_values(transformed_data, target_system)
        
        # Transform field names to match target system conventions
        transformed_data = self._transform_field_names(transformed_data, target_system)
        
        return transformed_data
    
    def _transform_timestamps(self, data: Dict[str, Any], source_system: str, target_system: str) -> Dict[str, Any]:
        """Transform timestamp fields between systems"""
        timestamp_fields = ["created_at", "updated_at", "creation", "modified"]
        
        for field in timestamp_fields:
            if field in data and data[field]:
                try:
                    # Parse and reformat timestamp
                    if isinstance(data[field], str):
                        # Parse ISO format timestamp
                        dt = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
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
    
    def _transform_booleans(self, data: Dict[str, Any], source_system: str, target_system: str) -> Dict[str, Any]:
        """Transform boolean fields between systems"""
        boolean_fields = ["disabled", "enabled", "active", "inactive"]
        
        for field in boolean_fields:
            if field in data:
                value = data[field]
                
                # Convert to boolean if needed
                if isinstance(value, str):
                    if value.lower() in ["true", "1", "yes", "on"]:
                        data[field] = True
                    elif value.lower() in ["false", "0", "no", "off"]:
                        data[field] = False
                elif isinstance(value, int):
                    data[field] = bool(value)
        
        return data
    
    def _transform_null_values(self, data: Dict[str, Any], target_system: str) -> Dict[str, Any]:
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
    
    def _transform_field_names(self, data: Dict[str, Any], target_system: str) -> Dict[str, Any]:
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
        s1 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', text)
        # Convert to lowercase
        return s1.lower()
    
    def _add_system_metadata(self, data: Dict[str, Any], target_system: str) -> Dict[str, Any]:
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
    
    async def _apply_complex_mappings(self, data: Dict[str, Any], mapping_config: Dict[str, str], 
                                    source_system: str, target_system: str) -> Dict[str, Any]:
        """Apply complex mappings with lookup logic"""
        try:
            complex_mappings = mapping_config.get("complex_mappings", {})
            
            for field_name, complex_config in complex_mappings.items():
                if field_name in data:
                    mapped_value = await self.complex_mapper.map_complex_field(
                        field_name, data[field_name], mapping_config, 
                        f"{source_system}_to_{target_system}"
                    )
                    data[field_name] = mapped_value
            
            return data
            
        except Exception as e:
            logger.error("Complex mapping failed", error=str(e))
            return data
    
    def create_field_mapping(self, doctype: str, table: str, 
                           field_mappings: Dict[str, str]) -> Dict[str, str]:
        """Create a field mapping configuration"""
        return {
            "frappe_doctype": doctype,
            "supabase_table": table,
            "field_mappings": field_mappings,
            "sync_fields": list(field_mappings.keys())
        }
    
    def validate_mapping(self, mapping: Dict[str, str]) -> List[str]:
        """Validate a field mapping configuration"""
        errors = []
        
        required_fields = ["frappe_doctype", "supabase_table", "field_mappings"]
        for field in required_fields:
            if field not in mapping:
                errors.append(f"Missing required field: {field}")
        
        if "field_mappings" in mapping and not isinstance(mapping["field_mappings"], dict):
            errors.append("field_mappings must be a dictionary")
        
        return errors
