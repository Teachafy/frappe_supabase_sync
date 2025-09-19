# Schema Discovery & Intelligent Mapping Guide

## 🎯 **Overview**

The Frappe-Supabase Sync Service now includes **intelligent schema discovery** that automatically analyzes both Frappe doctypes and Supabase tables to create optimal field mappings and sync configurations.

## 🔧 **Environment Variables for Schema Discovery**

Add these variables to your `.env` file:

### **Core Discovery Settings**
```bash
# Enable schema discovery
ENABLE_SCHEMA_DISCOVERY=true
DISCOVERY_MODE=auto  # auto, manual, hybrid
SCHEMA_CACHE_TTL=3600  # Cache schema for 1 hour
AUTO_MAPPING_CONFIDENCE_THRESHOLD=0.8  # 80% confidence for auto-mapping
```

### **Frappe Discovery Configuration**
```bash
# Comma-separated list of doctypes to discover
FRAPPE_DISCOVERY_DOCTYPES=Employee,Customer,Item,Lead,Opportunity,User,Company,Branch,Department,Designation

# Common fields to include in all mappings
FRAPPE_DISCOVERY_FIELDS=name,creation,modified,owner,modified_by

# Fields to skip during discovery
FRAPPE_DISCOVERY_SKIP_FIELDS=__islocal,__unsaved,__user_tags,__comments
```

### **Supabase Discovery Configuration**
```bash
# Comma-separated list of tables to discover
SUPABASE_DISCOVERY_TABLES=employees,customers,items,leads,opportunities,users,companies,branches,departments,designations

# Tables to skip during discovery
SUPABASE_DISCOVERY_SKIP_TABLES=pg_,information_schema,pg_catalog

# Fields to skip during discovery
SUPABASE_DISCOVERY_SKIP_FIELDS=created_at,updated_at,id
```

### **Intelligent Mapping Settings**
```bash
# Enable smart field mapping
ENABLE_SMART_MAPPING=true
FIELD_SIMILARITY_THRESHOLD=0.7  # 70% similarity for field matching
ENABLE_FIELD_TYPE_MAPPING=true  # Map fields by type compatibility
ENABLE_SEMANTIC_MAPPING=true  # Use semantic analysis for field names
```

### **Data Type Mapping**
```bash
# Map Frappe field types to Supabase types
FRAPPE_TO_SUPABASE_TYPE_MAP={"Data": "text", "Int": "integer", "Float": "numeric", "Check": "boolean", "Date": "date", "Datetime": "timestamp", "Time": "time", "Text": "text", "Small Text": "text", "Long Text": "text", "Code": "text", "Link": "text", "Dynamic Link": "text", "Select": "text", "Read Only": "text", "Password": "text", "Attach": "text", "Attach Image": "text", "Signature": "text", "Color": "text", "Barcode": "text", "Geolocation": "text", "Duration": "integer", "Currency": "numeric", "Percent": "numeric"}
```

## 🚀 **Quick Start with Schema Discovery**

### **1. Configure Environment**
```bash
# Copy and edit environment file
cp .env.example .env

# Edit .env with your specific doctypes and tables
nano .env
```

### **2. Start the Service**
```bash
# Install dependencies
pip install -r requirements.txt

# Start the service
python main.py
```

### **3. Discover Schemas**
```bash
# Run schema discovery test
python test_schema_discovery.py

# Or use the API
curl -X POST http://localhost:8000/api/schema/discover
```

### **4. Review and Apply Mappings**
```bash
# Get discovered mappings
curl http://localhost:8000/api/schema/mappings

# Apply mappings to sync configuration
curl -X POST http://localhost:8000/api/schema/mappings/apply \
  -H "Content-Type: application/json" \
  -d '{"mappings": {...}}'
```

## 📊 **API Endpoints for Schema Discovery**

### **Discovery Endpoints**
- `POST /api/schema/discover` - Discover all schemas and create mappings
- `GET /api/schema/frappe` - Get discovered Frappe schemas
- `GET /api/schema/supabase` - Get discovered Supabase schemas
- `GET /api/schema/mappings` - Get intelligent field mappings
- `GET /api/schema/summary` - Get discovery summary

### **Individual Schema Endpoints**
- `GET /api/schema/frappe/{doctype}` - Get specific Frappe doctype schema
- `GET /api/schema/supabase/{table}` - Get specific Supabase table schema
- `GET /api/schema/compare/{doctype}/{table}` - Compare two schemas

### **Mapping Management Endpoints**
- `POST /api/schema/mappings/validate` - Validate a mapping configuration
- `POST /api/schema/mappings/apply` - Apply mappings to sync configuration

## 🔍 **How Schema Discovery Works**

### **1. Frappe Schema Discovery**
- Fetches doctype metadata from Frappe API
- Extracts field information (name, type, label, options, etc.)
- Gets sample data for analysis
- Skips system fields and specified skip fields

### **2. Supabase Schema Discovery**
- Queries table schema using RPC functions
- Falls back to sample data analysis if RPC unavailable
- Infers field types from sample data
- Skips system tables and specified skip tables

### **3. Intelligent Field Mapping**
- **Name Similarity**: Matches fields by name similarity (70% threshold)
- **Type Compatibility**: Ensures field types are compatible
- **Label Similarity**: Matches fields by label similarity
- **Semantic Analysis**: Uses context to improve matching

### **4. Mapping Confidence Scoring**
- Calculates confidence score for each mapping
- Only applies mappings above confidence threshold
- Provides detailed mapping analysis

## 📋 **Example Discovery Results**

### **Frappe Employee Doctype**
```json
{
  "doctype": "Employee",
  "label": "Employee",
  "module": "HR",
  "fields": [
    {
      "fieldname": "name",
      "label": "Employee ID",
      "fieldtype": "Data",
      "reqd": 1
    },
    {
      "fieldname": "employee_name",
      "label": "Employee Name",
      "fieldtype": "Data",
      "reqd": 1
    },
    {
      "fieldname": "email",
      "label": "Email",
      "fieldtype": "Data"
    }
  ],
  "total_fields": 45
}
```

### **Supabase Employees Table**
```json
{
  "table": "employees",
  "label": "Employees",
  "fields": [
    {
      "fieldname": "id",
      "label": "Id",
      "fieldtype": "integer"
    },
    {
      "fieldname": "full_name",
      "label": "Full Name",
      "fieldtype": "varchar"
    },
    {
      "fieldname": "email",
      "label": "Email",
      "fieldtype": "varchar"
    }
  ],
  "total_fields": 12
}
```

### **Intelligent Mapping**
```json
{
  "frappe_doctype": "Employee",
  "supabase_table": "employees",
  "field_mappings": {
    "name": "id",
    "employee_name": "full_name",
    "email": "email"
  },
  "confidence_score": 0.85,
  "direction": "bidirectional"
}
```

## 🛠️ **Customizing Discovery**

### **Adding New Doctypes**
```bash
# Add to FRAPPE_DISCOVERY_DOCTYPES
FRAPPE_DISCOVERY_DOCTYPES=Employee,Customer,Item,Lead,Opportunity,NewDoctype
```

### **Adding New Tables**
```bash
# Add to SUPABASE_DISCOVERY_TABLES
SUPABASE_DISCOVERY_TABLES=employees,customers,items,leads,opportunities,new_table
```

### **Adjusting Similarity Thresholds**
```bash
# Lower threshold for more aggressive matching
FIELD_SIMILARITY_THRESHOLD=0.6

# Higher threshold for more conservative matching
FIELD_SIMILARITY_THRESHOLD=0.8
```

### **Custom Field Mappings**
```python
# Override automatic mappings
custom_mapping = {
    "frappe_doctype": "Employee",
    "supabase_table": "employees",
    "field_mappings": {
        "name": "employee_id",  # Custom mapping
        "employee_name": "full_name",
        "email": "email_address"
    }
}
```

## 📈 **Monitoring Discovery**

### **View Discovery Status**
```bash
# Check discovery summary
curl http://localhost:8000/api/schema/summary

# View specific mappings
curl http://localhost:8000/api/schema/mappings
```

### **Compare Schemas**
```bash
# Compare specific doctype and table
curl http://localhost:8000/api/schema/compare/Employee/employees
```

### **Validate Mappings**
```bash
# Validate a mapping before applying
curl -X POST http://localhost:8000/api/schema/mappings/validate \
  -H "Content-Type: application/json" \
  -d '{"frappe_doctype": "Employee", "supabase_table": "employees", "field_mappings": {...}}'
```

## 🔧 **Troubleshooting**

### **Common Issues**

1. **No Schemas Discovered**
   - Check Frappe/Supabase API credentials
   - Verify doctype/table names in configuration
   - Check network connectivity

2. **Low Mapping Confidence**
   - Lower similarity threshold
   - Add custom field mappings
   - Check field naming conventions

3. **Missing Fields**
   - Add fields to discovery configuration
   - Check skip field settings
   - Verify field permissions

### **Debug Commands**
```bash
# Test individual schema discovery
python test_schema_discovery.py

# Test API endpoints
python test_api.py

# Check service logs
docker-compose logs -f sync-service
```

## 🎯 **Best Practices**

1. **Start Small**: Begin with a few key doctypes and tables
2. **Review Mappings**: Always review auto-generated mappings before applying
3. **Test Thoroughly**: Test mappings with sample data before production
4. **Monitor Performance**: Watch for performance impact with large schemas
5. **Backup Configuration**: Keep backups of working configurations

## 🚀 **Next Steps**

1. **Configure Discovery**: Set up your specific doctypes and tables
2. **Run Discovery**: Execute schema discovery to analyze your systems
3. **Review Mappings**: Examine the generated field mappings
4. **Apply Mappings**: Apply the mappings to your sync configuration
5. **Test Sync**: Test synchronization with sample data
6. **Monitor Operations**: Monitor sync operations and performance

---

**The schema discovery system makes it easy to set up intelligent synchronization between your Frappe and Supabase systems!** 🎉
