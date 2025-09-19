"""
API endpoints for schema discovery and management
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
import structlog

from ..discovery.schema_discovery import SchemaDiscovery
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/schema", tags=["schema"])

# Initialize schema discovery
schema_discovery = SchemaDiscovery()


@router.post("/discover")
async def discover_schemas(background_tasks: BackgroundTasks):
    """Discover schemas from both Frappe and Supabase"""
    try:
        logger.info("Starting schema discovery")
        
        # Run discovery in background
        discovery_result = await schema_discovery.discover_all_schemas()
        
        return {
            "status": "success",
            "message": "Schema discovery completed",
            "result": discovery_result
        }
        
    except Exception as e:
        logger.error("Schema discovery failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Schema discovery failed: {str(e)}")


@router.get("/frappe")
async def get_frappe_schemas():
    """Get discovered Frappe schemas"""
    try:
        frappe_schemas = await schema_discovery.discover_frappe_schemas()
        
        return {
            "status": "success",
            "schemas": frappe_schemas,
            "count": len(frappe_schemas)
        }
        
    except Exception as e:
        logger.error("Failed to get Frappe schemas", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get Frappe schemas: {str(e)}")


@router.get("/supabase")
async def get_supabase_schemas():
    """Get discovered Supabase schemas"""
    try:
        supabase_schemas = await schema_discovery.discover_supabase_schemas()
        
        return {
            "status": "success",
            "schemas": supabase_schemas,
            "count": len(supabase_schemas)
        }
        
    except Exception as e:
        logger.error("Failed to get Supabase schemas", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get Supabase schemas: {str(e)}")


@router.get("/mappings")
async def get_intelligent_mappings():
    """Get intelligent field mappings"""
    try:
        frappe_schemas = await schema_discovery.discover_frappe_schemas()
        supabase_schemas = await schema_discovery.discover_supabase_schemas()
        mappings = await schema_discovery.create_intelligent_mappings(frappe_schemas, supabase_schemas)
        
        return {
            "status": "success",
            "mappings": mappings,
            "count": len(mappings)
        }
        
    except Exception as e:
        logger.error("Failed to get intelligent mappings", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get intelligent mappings: {str(e)}")


@router.get("/summary")
async def get_schema_summary():
    """Get schema discovery summary"""
    try:
        summary = await schema_discovery.get_schema_summary()
        
        return {
            "status": "success",
            "summary": summary
        }
        
    except Exception as e:
        logger.error("Failed to get schema summary", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get schema summary: {str(e)}")


@router.get("/frappe/{doctype}")
async def get_frappe_doctype_schema(doctype: str):
    """Get detailed schema for a specific Frappe doctype"""
    try:
        schema = await schema_discovery._get_frappe_doctype_schema(doctype, [])
        
        if not schema:
            raise HTTPException(status_code=404, detail=f"Doctype {doctype} not found")
        
        return {
            "status": "success",
            "schema": schema
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Frappe doctype schema for {doctype}", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get doctype schema: {str(e)}")


@router.get("/supabase/{table}")
async def get_supabase_table_schema(table: str):
    """Get detailed schema for a specific Supabase table"""
    try:
        schema = await schema_discovery._get_supabase_table_schema(table, [])
        
        if not schema:
            raise HTTPException(status_code=404, detail=f"Table {table} not found")
        
        return {
            "status": "success",
            "schema": schema
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Supabase table schema for {table}", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get table schema: {str(e)}")


@router.post("/mappings/validate")
async def validate_mapping(mapping: Dict[str, Any]):
    """Validate a field mapping configuration"""
    try:
        # Validate required fields
        required_fields = ["frappe_doctype", "supabase_table", "field_mappings"]
        for field in required_fields:
            if field not in mapping:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Validate field mappings
        if not isinstance(mapping["field_mappings"], dict):
            raise HTTPException(status_code=400, detail="field_mappings must be a dictionary")
        
        # Validate sync fields
        if "sync_fields" in mapping and not isinstance(mapping["sync_fields"], list):
            raise HTTPException(status_code=400, detail="sync_fields must be a list")
        
        return {
            "status": "success",
            "message": "Mapping validation passed",
            "mapping": mapping
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Mapping validation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Mapping validation failed: {str(e)}")


@router.post("/mappings/apply")
async def apply_mappings(mappings: Dict[str, Any]):
    """Apply discovered mappings to sync configuration"""
    try:
        from ..config import settings
        
        # Validate mappings
        for mapping_name, mapping in mappings.items():
            if not isinstance(mapping, dict):
                raise HTTPException(status_code=400, detail=f"Invalid mapping for {mapping_name}")
            
            required_fields = ["frappe_doctype", "supabase_table", "field_mappings"]
            for field in required_fields:
                if field not in mapping:
                    raise HTTPException(status_code=400, detail=f"Missing {field} in {mapping_name}")
        
        # Apply mappings to settings
        settings.sync_mappings.update(mappings)
        
        logger.info("Mappings applied successfully", mappings=list(mappings.keys()))
        
        return {
            "status": "success",
            "message": "Mappings applied successfully",
            "applied_mappings": list(mappings.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to apply mappings", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to apply mappings: {str(e)}")


@router.get("/compare/{doctype}/{table}")
async def compare_schemas(doctype: str, table: str):
    """Compare Frappe doctype and Supabase table schemas"""
    try:
        # Get both schemas
        frappe_schema = await schema_discovery._get_frappe_doctype_schema(doctype, [])
        supabase_schema = await schema_discovery._get_supabase_table_schema(table, [])
        
        if not frappe_schema:
            raise HTTPException(status_code=404, detail=f"Frappe doctype {doctype} not found")
        
        if not supabase_schema:
            raise HTTPException(status_code=404, detail=f"Supabase table {table} not found")
        
        # Create comparison
        comparison = {
            "frappe_doctype": doctype,
            "supabase_table": table,
            "frappe_fields": len(frappe_schema.get("fields", [])),
            "supabase_fields": len(supabase_schema.get("fields", [])),
            "potential_mappings": [],
            "unmapped_frappe_fields": [],
            "unmapped_supabase_fields": []
        }
        
        # Find potential mappings
        frappe_fields = {f["fieldname"]: f for f in frappe_schema.get("fields", [])}
        supabase_fields = {f["fieldname"]: f for f in supabase_schema.get("fields", [])}
        
        for frappe_field_name, frappe_field in frappe_fields.items():
            best_match = schema_discovery._find_best_field_match(
                frappe_field, 
                list(supabase_fields.values())
            )
            
            if best_match:
                comparison["potential_mappings"].append({
                    "frappe_field": frappe_field_name,
                    "supabase_field": best_match["fieldname"],
                    "confidence": schema_discovery._calculate_field_similarity(frappe_field, best_match)
                })
            else:
                comparison["unmapped_frappe_fields"].append(frappe_field_name)
        
        # Find unmapped Supabase fields
        mapped_supabase_fields = {m["supabase_field"] for m in comparison["potential_mappings"]}
        comparison["unmapped_supabase_fields"] = [
            field_name for field_name in supabase_fields.keys() 
            if field_name not in mapped_supabase_fields
        ]
        
        return {
            "status": "success",
            "comparison": comparison
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare schemas for {doctype} and {table}", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to compare schemas: {str(e)}")
