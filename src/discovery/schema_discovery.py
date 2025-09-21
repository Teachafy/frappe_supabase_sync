"""
Schema discovery engine for Frappe and Supabase
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from difflib import SequenceMatcher

from ..config import settings
from ..utils.frappe_client import FrappeClient
from ..utils.supabase_client import SupabaseClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SchemaDiscovery:
    """Discovers and analyzes schemas from both Frappe and Supabase"""

    def __init__(self):
        self.frappe_client = FrappeClient()
        self.supabase_client = SupabaseClient()
        self.schema_cache = {}
        self.cache_ttl = settings.schema_cache_ttl

    async def discover_frappe_doctypes(self) -> Dict[str, Any]:
        """Discover Frappe doctypes and their fields"""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.frappe_url}/api/method/frappe.desk.form.load.getdoctype",
                    params={"doctype": "Employee"},  # Example doctype
                )
                if response.status_code == 200:
                    data = await response.json()
                    docs = data.get("docs", [])
                    return {
                        doc.get("name", f"doctype_{i}"): doc
                        for i, doc in enumerate(docs)
                    }
                return {}
        except Exception as e:
            logger.error(f"Failed to discover Frappe doctypes: {e}")
            return {}

    async def discover_supabase_tables(self) -> Dict[str, Any]:
        """Discover Supabase tables and their columns"""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.supabase_url}/rest/v1/rpc/get_all_tables",
                    headers={
                        "Authorization": f"Bearer {settings.supabase_service_role_key}"
                    },
                )
                if response.status_code == 200:
                    data = await response.json()
                    return {table["table_name"]: table for table in data}
                return {}
        except Exception as e:
            logger.error(f"Failed to discover Supabase tables: {e}")
            return {}

    async def discover_event_related_doctypes(self) -> Dict[str, List[str]]:
        """Discover event-related doctypes in both systems"""
        frappe_doctypes = await self.discover_frappe_doctypes()
        supabase_tables = await self.discover_supabase_tables()

        event_related = {"frappe": [], "supabase": []}

        # Look for event-related patterns
        for doctype_name in frappe_doctypes.keys():
            if "event" in doctype_name.lower() or "training" in doctype_name.lower():
                event_related["frappe"].append(doctype_name)

        for table_name in supabase_tables.keys():
            if "event" in table_name.lower() or "training" in table_name.lower():
                event_related["supabase"].append(table_name)

        return event_related

    async def discover_all_schemas(self) -> Dict[str, Any]:
        """Discover schemas from both systems and create mappings"""
        try:
            logger.info("Starting comprehensive schema discovery")

            # Discover Frappe schemas
            frappe_schemas = await self.discover_frappe_schemas()
            logger.info(f"Discovered {len(frappe_schemas)} Frappe doctypes")

            # Discover Supabase schemas
            supabase_schemas = await self.discover_supabase_schemas()
            logger.info(f"Discovered {len(supabase_schemas)} Supabase tables")

            # Create intelligent mappings
            mappings = await self.create_intelligent_mappings(
                frappe_schemas, supabase_schemas
            )
            logger.info(f"Created {len(mappings)} intelligent mappings")

            return {
                "frappe_schemas": frappe_schemas,
                "supabase_schemas": supabase_schemas,
                "mappings": mappings,
                "discovery_timestamp": datetime.utcnow().isoformat(),
                "total_doctypes": len(frappe_schemas),
                "total_tables": len(supabase_schemas),
                "total_mappings": len(mappings),
            }

        except Exception as e:
            logger.error("Schema discovery failed", error=str(e))
            raise

    async def discover_frappe_schemas(self) -> Dict[str, Any]:
        """Discover Frappe doctype schemas"""
        try:
            doctypes = (
                settings.frappe_discovery_doctypes.split(",")
                if hasattr(settings, "frappe_discovery_doctypes")
                else []
            )
            skip_fields = (
                settings.frappe_discovery_skip_fields.split(",")
                if hasattr(settings, "frappe_discovery_skip_fields")
                else []
            )

            schemas = {}

            for doctype in doctypes:
                doctype = doctype.strip()
                if not doctype:
                    continue

                try:
                    schema = await self._get_frappe_doctype_schema(doctype, skip_fields)
                    if schema:
                        schemas[doctype] = schema
                        logger.info(f"Discovered Frappe doctype: {doctype}")
                except Exception as e:
                    logger.warning(
                        f"Failed to discover Frappe doctype {doctype}", error=str(e)
                    )

            return schemas

        except Exception as e:
            logger.error("Frappe schema discovery failed", error=str(e))
            return {}

    async def _get_frappe_doctype_schema(
        self, doctype: str, skip_fields: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get detailed schema for a Frappe doctype"""
        try:
            # Get doctype meta
            meta = await self.frappe_client.get_doctype_meta(doctype)

            if not meta:
                return None

            # Extract field information
            fields = []
            for field in meta.get("fields", []):
                if field.get("fieldname") in skip_fields:
                    continue

                field_info = {
                    "fieldname": field.get("fieldname"),
                    "label": field.get("label"),
                    "fieldtype": field.get("fieldtype"),
                    "options": field.get("options"),
                    "reqd": field.get("reqd", 0),
                    "read_only": field.get("read_only", 0),
                    "hidden": field.get("hidden", 0),
                    "description": field.get("description", ""),
                    "default": field.get("default"),
                    "length": field.get("length"),
                    "precision": field.get("precision"),
                }
                fields.append(field_info)

            # Get sample data for analysis
            sample_data = await self.frappe_client.get_documents(doctype, limit=5)

            return {
                "doctype": doctype,
                "label": meta.get("label", doctype),
                "module": meta.get("module"),
                "fields": fields,
                "sample_data": sample_data,
                "total_fields": len(fields),
                "discovered_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get Frappe schema for {doctype}", error=str(e))
            return None

    async def discover_supabase_schemas(self) -> Dict[str, Any]:
        """Discover Supabase table schemas"""
        try:
            tables = (
                settings.supabase_discovery_tables.split(",")
                if hasattr(settings, "supabase_discovery_tables")
                else []
            )
            skip_tables = (
                settings.supabase_discovery_skip_tables.split(",")
                if hasattr(settings, "supabase_discovery_skip_tables")
                else []
            )
            skip_fields = (
                settings.supabase_discovery_skip_fields.split(",")
                if hasattr(settings, "supabase_discovery_skip_fields")
                else []
            )

            schemas = {}

            for table in tables:
                table = table.strip()
                if not table or table in skip_tables:
                    continue

                try:
                    schema = await self._get_supabase_table_schema(table, skip_fields)
                    if schema:
                        schemas[table] = schema
                        logger.info(f"Discovered Supabase table: {table}")
                except Exception as e:
                    logger.warning(
                        f"Failed to discover Supabase table {table}", error=str(e)
                    )

            return schemas

        except Exception as e:
            logger.error("Supabase schema discovery failed", error=str(e))
            return {}

    async def _get_supabase_table_schema(
        self, table: str, skip_fields: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get detailed schema for a Supabase table"""
        try:
            # Get table schema using RPC function
            schema_info = await self.supabase_client.execute_rpc(
                "get_table_schema", {"table_name": table}
            )

            if not schema_info:
                # Fallback: get sample data and infer schema
                sample_data = await self.supabase_client.get_records(table, limit=5)
                if not sample_data:
                    return None

                # Infer schema from sample data
                fields = []
                for record in sample_data:
                    for field_name, value in record.items():
                        if field_name in skip_fields:
                            continue

                        field_type = self._infer_field_type(value)
                        field_info = {
                            "fieldname": field_name,
                            "label": self._format_field_label(field_name),
                            "fieldtype": field_type,
                            "nullable": value is None,
                            "sample_value": value,
                        }

                        # Avoid duplicates
                        if not any(f["fieldname"] == field_name for f in fields):
                            fields.append(field_info)

                schema_info = {"table_name": table, "columns": fields}

            # Get sample data
            sample_data = await self.supabase_client.get_records(table, limit=5)

            return {
                "table": table,
                "label": self._format_table_label(table),
                "fields": schema_info.get("columns", []),
                "sample_data": sample_data,
                "total_fields": len(schema_info.get("columns", [])),
                "discovered_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get Supabase schema for {table}", error=str(e))
            return None

    def _infer_field_type(self, value: Any) -> str:
        """Infer field type from sample value"""
        if value is None:
            return "text"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "numeric"
        elif isinstance(value, str):
            if len(value) > 255:
                return "text"
            else:
                return "varchar"
        elif isinstance(value, (list, dict)):
            return "jsonb"
        else:
            return "text"

    def _format_field_label(self, field_name: str) -> str:
        """Format field name into a readable label"""
        return field_name.replace("_", " ").title()

    def _format_table_label(self, table_name: str) -> str:
        """Format table name into a readable label"""
        return table_name.replace("_", " ").title()

    async def create_intelligent_mappings(
        self, frappe_schemas: Dict[str, Any], supabase_schemas: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create intelligent field mappings between Frappe and Supabase"""
        try:
            mappings = {}

            # Find potential matches based on table/doctype names
            for doctype, frappe_schema in frappe_schemas.items():
                best_match = self._find_best_table_match(doctype, supabase_schemas)

                if best_match:
                    table_name, supabase_schema = best_match
                    mapping = await self._create_field_mapping(
                        doctype, frappe_schema, table_name, supabase_schema
                    )
                    if mapping:
                        mappings[f"{doctype}_{table_name}"] = mapping

            return mappings

        except Exception as e:
            logger.error("Failed to create intelligent mappings", error=str(e))
            return {}

    def _find_best_table_match(
        self, doctype: str, supabase_schemas: Dict[str, Any]
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Find the best matching Supabase table for a Frappe doctype"""
        best_match = None
        best_score = 0

        for table_name, supabase_schema in supabase_schemas.items():
            score = self._calculate_similarity_score(doctype, table_name)
            if score > best_score and score > 0.5:  # 50% similarity threshold
                best_score = score
                best_match = (table_name, supabase_schema)

        return best_match

    def _calculate_similarity_score(self, doctype: str, table_name: str) -> float:
        """Calculate similarity score between doctype and table name"""
        # Normalize names
        doctype_norm = doctype.lower().replace("_", "")
        table_norm = table_name.lower().replace("_", "")

        # Calculate similarity
        similarity = SequenceMatcher(None, doctype_norm, table_norm).ratio()

        # Boost score for exact matches or common patterns
        if doctype_norm == table_norm:
            similarity = 1.0
        elif doctype_norm in table_norm or table_norm in doctype_norm:
            similarity = max(similarity, 0.8)

        return similarity

    async def _create_field_mapping(
        self,
        doctype: str,
        frappe_schema: Dict[str, Any],
        table_name: str,
        supabase_schema: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Create field mapping between Frappe doctype and Supabase table"""
        try:
            field_mappings = {}
            sync_fields = []

            # Map fields based on similarity and type compatibility
            for frappe_field in frappe_schema.get("fields", []):
                best_match = self._find_best_field_match(
                    frappe_field, supabase_schema.get("fields", [])
                )

                if best_match:
                    supabase_field = best_match
                    field_mappings[frappe_field["fieldname"]] = supabase_field[
                        "fieldname"
                    ]
                    sync_fields.append(frappe_field["fieldname"])

            # Add reverse mappings for bidirectional sync
            reverse_mappings = {v: k for k, v in field_mappings.items()}

            return {
                "frappe_doctype": doctype,
                "supabase_table": table_name,
                "primary_key": "name",  # Frappe default
                "sync_fields": sync_fields,
                "field_mappings": field_mappings,
                "reverse_mappings": reverse_mappings,
                "direction": settings.default_sync_direction,
                "conflict_resolution": settings.conflict_resolution_strategy,
                "confidence_score": self._calculate_mapping_confidence(
                    field_mappings, sync_fields
                ),
                "created_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(
                f"Failed to create field mapping for {doctype} -> {table_name}",
                error=str(e),
            )
            return None

    def _find_best_field_match(
        self, frappe_field: Dict[str, Any], supabase_fields: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find the best matching Supabase field for a Frappe field"""
        best_match = None
        best_score = 0

        for supabase_field in supabase_fields:
            score = self._calculate_field_similarity(frappe_field, supabase_field)
            if score > best_score and score > settings.field_similarity_threshold:
                best_score = score
                best_match = supabase_field

        return best_match

    def _calculate_field_similarity(
        self, frappe_field: Dict[str, Any], supabase_field: Dict[str, Any]
    ) -> float:
        """Calculate similarity between Frappe and Supabase fields"""
        frappe_name = frappe_field.get("fieldname", "").lower()
        supabase_name = supabase_field.get("fieldname", "").lower()

        # Name similarity
        name_similarity = SequenceMatcher(None, frappe_name, supabase_name).ratio()

        # Type compatibility
        type_compatibility = self._check_type_compatibility(
            frappe_field.get("fieldtype"), supabase_field.get("fieldtype")
        )

        # Label similarity
        frappe_label = frappe_field.get("label", "").lower()
        supabase_label = supabase_field.get("label", "").lower()
        label_similarity = SequenceMatcher(None, frappe_label, supabase_label).ratio()

        # Weighted score
        total_score = (
            name_similarity * 0.4 + type_compatibility * 0.3 + label_similarity * 0.3
        )

        return total_score

    def _check_type_compatibility(self, frappe_type: str, supabase_type: str) -> float:
        """Check type compatibility between Frappe and Supabase field types"""
        type_mapping = {
            "Data": ["varchar", "text"],
            "Int": ["integer", "bigint"],
            "Float": ["numeric", "real", "double precision"],
            "Check": ["boolean"],
            "Date": ["date"],
            "Datetime": ["timestamp", "timestamptz"],
            "Time": ["time"],
            "Text": ["text", "varchar"],
            "Long Text": ["text"],
            "Code": ["text", "varchar"],
            "Link": ["text", "varchar"],
            "Select": ["text", "varchar"],
            "Currency": ["numeric", "money"],
            "Percent": ["numeric"],
        }

        if not frappe_type or not supabase_type:
            return 0.0

        compatible_types = type_mapping.get(frappe_type, [])
        if supabase_type in compatible_types:
            return 1.0
        elif any(t in supabase_type for t in compatible_types):
            return 0.8
        else:
            return 0.0

    def _calculate_mapping_confidence(
        self, field_mappings: Dict[str, str], sync_fields: List[str]
    ) -> float:
        """Calculate confidence score for the mapping"""
        if not field_mappings:
            return 0.0

        total_fields = len(sync_fields)
        mapped_fields = len(field_mappings)

        return mapped_fields / total_fields if total_fields > 0 else 0.0

    async def get_schema_summary(self) -> Dict[str, Any]:
        """Get a summary of discovered schemas"""
        try:
            discovery_result = await self.discover_all_schemas()

            summary = {
                "discovery_timestamp": discovery_result["discovery_timestamp"],
                "frappe_doctypes": list(discovery_result["frappe_schemas"].keys()),
                "supabase_tables": list(discovery_result["supabase_schemas"].keys()),
                "mappings": list(discovery_result["mappings"].keys()),
                "total_doctypes": discovery_result["total_doctypes"],
                "total_tables": discovery_result["total_tables"],
                "total_mappings": discovery_result["total_mappings"],
            }

            return summary

        except Exception as e:
            logger.error("Failed to get schema summary", error=str(e))
            return {}
