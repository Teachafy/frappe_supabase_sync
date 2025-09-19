"""
Configuration management for Frappe-Supabase Sync Service
"""
import os
from typing import Any, Dict, List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Frappe Configuration
    frappe_url: str = Field(..., env="FRAPPE_URL")
    frappe_api_key: str = Field(..., env="FRAPPE_API_KEY")
    frappe_api_secret: str = Field(..., env="FRAPPE_API_SECRET")
    
    # Supabase Configuration
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_anon_key: str = Field(..., env="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(..., env="SUPABASE_SERVICE_ROLE_KEY")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Sync Configuration
    sync_batch_size: int = Field(default=100, env="SYNC_BATCH_SIZE")
    sync_retry_attempts: int = Field(default=3, env="SYNC_RETRY_ATTEMPTS")
    sync_retry_delay: int = Field(default=5, env="SYNC_RETRY_DELAY")
    conflict_resolution_strategy: str = Field(default="last_modified_wins", env="CONFLICT_RESOLUTION_STRATEGY")
    
    # Webhook Security
    webhook_secret: str = Field(..., env="WEBHOOK_SECRET")
    frappe_webhook_token: str = Field(..., env="FRAPPE_WEBHOOK_TOKEN")
    
    # Monitoring
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Sync Table Mappings (configured via environment or config file)
    sync_mappings: Dict[str, Dict[str, Any]] = Field(
        default={
            "Employee": {
                "frappe_doctype": "Employee",
                "supabase_table": "employees",
                "primary_key": "name",
                "sync_fields": ["name", "employee_name", "email", "mobile_number", "status"]
            },
            "Customer": {
                "frappe_doctype": "Customer", 
                "supabase_table": "customers",
                "primary_key": "name",
                "sync_fields": ["name", "customer_name", "email_id", "mobile_no", "disabled"]
            }
        }
    )
    
    # Schema Discovery Configuration
    enable_schema_discovery: bool = Field(default=True, env="ENABLE_SCHEMA_DISCOVERY")
    discovery_mode: str = Field(default="auto", env="DISCOVERY_MODE")
    schema_cache_ttl: int = Field(default=3600, env="SCHEMA_CACHE_TTL")
    auto_mapping_confidence_threshold: float = Field(default=0.8, env="AUTO_MAPPING_CONFIDENCE_THRESHOLD")
    
    # Frappe Discovery Configuration
    frappe_discovery_doctypes: str = Field(default="Employee,Customer,Item", env="FRAPPE_DISCOVERY_DOCTYPES")
    frappe_discovery_fields: str = Field(default="name,creation,modified,owner,modified_by", env="FRAPPE_DISCOVERY_FIELDS")
    frappe_discovery_skip_fields: str = Field(default="__islocal,__unsaved,__user_tags,__comments", env="FRAPPE_DISCOVERY_SKIP_FIELDS")
    
    # Supabase Discovery Configuration
    supabase_discovery_tables: str = Field(default="employees,customers,items", env="SUPABASE_DISCOVERY_TABLES")
    supabase_discovery_skip_tables: str = Field(default="pg_,information_schema,pg_catalog", env="SUPABASE_DISCOVERY_SKIP_TABLES")
    supabase_discovery_skip_fields: str = Field(default="created_at,updated_at,id", env="SUPABASE_DISCOVERY_SKIP_FIELDS")
    
    # Field Mapping Intelligence
    enable_smart_mapping: bool = Field(default=True, env="ENABLE_SMART_MAPPING")
    field_similarity_threshold: float = Field(default=0.7, env="FIELD_SIMILARITY_THRESHOLD")
    enable_field_type_mapping: bool = Field(default=True, env="ENABLE_FIELD_TYPE_MAPPING")
    enable_semantic_mapping: bool = Field(default=True, env="ENABLE_SEMANTIC_MAPPING")
    
    # Data Type Mapping Configuration
    frappe_to_supabase_type_map: Dict[str, str] = Field(
        default={
            "Data": "text", "Int": "integer", "Float": "numeric", "Check": "boolean",
            "Date": "date", "Datetime": "timestamp", "Time": "time", "Text": "text",
            "Small Text": "text", "Long Text": "text", "Code": "text", "Link": "text",
            "Dynamic Link": "text", "Select": "text", "Read Only": "text", "Password": "text",
            "Attach": "text", "Attach Image": "text", "Signature": "text", "Color": "text",
            "Barcode": "text", "Geolocation": "text", "Duration": "integer",
            "Currency": "numeric", "Percent": "numeric"
        },
        env="FRAPPE_TO_SUPABASE_TYPE_MAP"
    )
    
    # Sync Rules Configuration
    default_sync_direction: str = Field(default="bidirectional", env="DEFAULT_SYNC_DIRECTION")
    enable_cascade_sync: bool = Field(default=True, env="ENABLE_CASCADE_SYNC")
    cascade_sync_depth: int = Field(default=2, env="CASCADE_SYNC_DEPTH")
    enable_conditional_sync: bool = Field(default=True, env="ENABLE_CONDITIONAL_SYNC")
    
    # Advanced Configuration
    enable_schema_validation: bool = Field(default=True, env="ENABLE_SCHEMA_VALIDATION")
    enable_data_validation: bool = Field(default=True, env="ENABLE_DATA_VALIDATION")
    enable_performance_optimization: bool = Field(default=True, env="ENABLE_PERFORMANCE_OPTIMIZATION")
    max_concurrent_syncs: int = Field(default=10, env="MAX_CONCURRENT_SYNCS")
    sync_timeout: int = Field(default=300, env="SYNC_TIMEOUT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_sync_mapping(doctype: str) -> Optional[Dict[str, str]]:
    """Get sync mapping configuration for a specific doctype"""
    return settings.sync_mappings.get(doctype)


def get_all_sync_mappings() -> Dict[str, Dict[str, str]]:
    """Get all sync mapping configurations"""
    return settings.sync_mappings


def add_sync_mapping(doctype: str, mapping: Dict[str, str]) -> None:
    """Add or update a sync mapping configuration"""
    settings.sync_mappings[doctype] = mapping


def remove_sync_mapping(doctype: str) -> None:
    """Remove a sync mapping configuration"""
    if doctype in settings.sync_mappings:
        del settings.sync_mappings[doctype]
