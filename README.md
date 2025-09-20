# Frappe-Supabase Sync Service

A robust 2-way synchronization service that maintains data consistency between Frappe and Supabase instances using webhook-triggered Docker services.

## 🎯 **Overview**

This service provides real-time, bidirectional synchronization between Frappe ERPNext and Supabase databases, ensuring data consistency across both systems. It handles create, update, and delete operations with intelligent conflict resolution and comprehensive monitoring.

## 🏗️ **Architecture**

### **Core Components**
- **Webhook Handlers**: Receive events from both Frappe and Supabase
- **Sync Engine**: Core synchronization logic with conflict resolution
- **Field Mapper**: Data transformation and field mapping between systems
- **Queue System**: Redis-based queue for managing sync operations
- **Monitoring**: Health checks, metrics, and logging

### **Data Flow**
```
Frappe Webhook → Sync Engine → Field Mapper → Supabase
     ↑                                    ↓
     ←─── Conflict Resolution ←─── Sync Engine ←─── Supabase Webhook
```

## 📁 **Project Structure**

```
frappe_supabase_sync/
├── src/                          # Core source code
│   ├── api/                      # API endpoints
│   ├── discovery/                # Schema discovery
│   ├── engine/                   # Sync engine core
│   ├── handlers/                 # Webhook handlers
│   ├── mapping/                  # Field mapping logic
│   ├── monitoring/               # Health & metrics
│   ├── queue/                    # Queue management
│   └── utils/                    # Utility functions
├── scripts/                      # Utility scripts (organized by function)
│   ├── debugging/                # Debug and check scripts
│   ├── schema-discovery/         # Schema analysis scripts
│   ├── setup/                    # Setup and configuration scripts
│   ├── testing/                  # Test runners and test fixes
│   └── verification/             # System verification scripts
├── tests/                        # Test suite
│   ├── test_*.py                 # Individual test files
│   └── conftest.py               # Pytest configuration
├── docs/                         # Documentation
├── config/                       # Configuration files
└── main.py                       # Application entry point
```

### **Script Organization Guidelines**
- **`scripts/debugging/`**: Debug and diagnostic scripts
- **`scripts/schema-discovery/`**: Schema analysis and discovery
- **`scripts/setup/`**: Initial setup and configuration
- **`scripts/testing/`**: Test runners and test utilities
- **`scripts/verification/`**: System verification and validation

## 🚀 **Quick Start**

### **Prerequisites**
- Docker and Docker Compose
- Frappe instance with API access
- Supabase project with service role key
- Redis instance (included in Docker Compose)

### **1. Clone and Setup**
```bash
git clone <repository-url>
cd frappe_supabase_sync
cp .env.example .env
```

### **2. Configure Environment**
Edit `.env` file with your credentials:
```bash
# Frappe Configuration
FRAPPE_URL=https://your-frappe-instance.com
FRAPPE_API_KEY=your_frappe_api_key
FRAPPE_API_SECRET=your_frappe_api_secret

# Supabase Configuration
SUPABASE_URL=https://your-supabase-instance.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Webhook Security
WEBHOOK_SECRET_KEY=your_webhook_secret_key
FRAPPE_WEBHOOK_TOKEN=your_frappe_webhook_token
```

### **3. Start Services**
```bash
docker-compose up -d
```

### **4. Verify Installation**
```bash
curl http://localhost:8000/health
```

## 📋 **Configuration**

### **Sync Mappings**

Configure which Frappe doctypes sync with which Supabase tables:

```python
sync_mappings = {
    "Employee": {
        "frappe_doctype": "Employee",
        "supabase_table": "employees",
        "primary_key": "name",
        "sync_fields": ["name", "employee_name", "email", "mobile_number", "status"],
        "field_mappings": {
            "name": "id",
            "employee_name": "full_name",
            "mobile_number": "phone"
        },
        "direction": "bidirectional",
        "conflict_resolution": "last_modified_wins"
    }
}
```

### **Field Mappings**

Map fields between Frappe and Supabase:
- **Direct mapping**: `"frappe_field": "supabase_field"`
- **Transformation**: Automatic data type conversion
- **Default mappings**: Built-in common field mappings

### **Conflict Resolution Strategies**

1. **`last_modified_wins`**: Use the most recently modified record
2. **`frappe_wins`**: Always use Frappe data
3. **`supabase_wins`**: Always use Supabase data
4. **`manual`**: Require manual resolution

## 🔧 **API Endpoints**

### **Webhook Endpoints**
- `POST /webhook/frappe` - Frappe webhook receiver
- `POST /webhook/supabase` - Supabase webhook receiver

### **Management Endpoints**
- `GET /health` - Health check
- `GET /metrics` - Service metrics
- `GET /sync/status` - Sync service status
- `GET /sync/mappings` - Current sync mappings
- `POST /sync/mappings` - Update sync mappings
- `POST /sync/retry-failed` - Retry failed operations

### **Monitoring Endpoints**
- `GET /sync/operations/{operation_id}` - Get operation details
- `GET /sync/operations/failed` - Get failed operations

## 🔄 **Webhook Setup**

### **Frappe Webhook Configuration**

1. **Create Webhook in Frappe**:
   - Go to Setup → Integrations → Webhooks
   - Create new webhook with:
     - **URL**: `https://your-sync-service.com/webhook/frappe`
     - **Method**: POST
     - **Doctype**: Select doctypes to sync
     - **Events**: After Insert, After Update, After Delete
     - **Secret**: Use your `FRAPPE_WEBHOOK_TOKEN`

2. **Test Webhook**:
   ```bash
   curl -X POST https://your-sync-service.com/webhook/frappe \
     -H "Content-Type: application/json" \
     -H "X-Frappe-Signature: your_signature" \
     -d '{"test": "data"}'
   ```

### **Supabase Webhook Configuration**

1. **Create Webhook in Supabase**:
   - Go to Database → Webhooks
   - Create new webhook with:
     - **Table**: Select tables to sync
     - **Events**: Insert, Update, Delete
     - **URL**: `https://your-sync-service.com/webhook/supabase`
     - **Secret**: Use your `WEBHOOK_SECRET_KEY`

2. **Test Webhook**:
   ```bash
   curl -X POST https://your-sync-service.com/webhook/supabase \
     -H "Content-Type: application/json" \
     -H "X-Supabase-Signature: your_signature" \
     -d '{"test": "data"}'
   ```

## 📊 **Monitoring & Observability**

### **Health Checks**
- **Endpoint**: `GET /health`
- **Checks**: Frappe API, Supabase API, Redis, Database
- **Response**: Overall health status and individual check results

### **Metrics**
- **Endpoint**: `GET /metrics`
- **Metrics**: Webhook counts, sync operations, durations, errors
- **Prometheus**: Compatible metrics format

### **Logging**
- **Structured Logging**: JSON format with context
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Log Files**: Stored in `/app/logs` directory

### **Grafana Dashboard**
Access Grafana at `http://localhost:3000` (admin/admin) for visual monitoring.

## 🛠️ **Development**

### **Local Development**
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export $(cat .env | xargs)

# Run the service
python main.py
```

### **Testing**
```bash
# Run tests
pytest tests/

# Test webhook endpoints
python tests/test_webhooks.py
```

### **Code Structure**
```
frappe_supabase_sync/
├── src/
│   ├── handlers/          # Webhook handlers
│   ├── engine/            # Sync engine
│   ├── mapping/           # Field mapping
│   ├── queue/             # Queue system
│   ├── monitoring/        # Health & metrics
│   └── utils/             # Utilities
├── config/                # Configuration files
├── tests/                 # Test files
├── docs/                  # Documentation
├── main.py               # FastAPI application
├── Dockerfile            # Docker configuration
└── docker-compose.yml    # Docker Compose setup
```

## 🔒 **Security**

### **Webhook Security**
- **Signature Verification**: HMAC-SHA256 signatures
- **Token Authentication**: Secure webhook tokens
- **Rate Limiting**: Built-in rate limiting (configurable)

### **Data Security**
- **Encryption**: All data encrypted in transit
- **Access Control**: Service role keys for Supabase
- **Audit Logging**: Complete operation audit trail

## 🚨 **Troubleshooting**

### **Common Issues**

1. **Webhook Not Receiving Events**
   - Check webhook URL accessibility
   - Verify signature verification
   - Check Frappe/Supabase webhook configuration

2. **Sync Operations Failing**
   - Check API credentials
   - Verify field mappings
   - Review error logs

3. **High Memory Usage**
   - Check queue sizes
   - Review metrics for stuck operations
   - Consider increasing Redis memory

### **Debug Commands**
```bash
# Check service health
curl http://localhost:8000/health

# View sync status
curl http://localhost:8000/sync/status

# Get failed operations
curl http://localhost:8000/sync/operations/failed

# View logs
docker-compose logs -f sync-service
```

## 📈 **Performance Optimization**

### **Queue Management**
- **Batch Processing**: Process multiple operations together
- **Priority Queues**: Prioritize critical operations
- **Retry Logic**: Exponential backoff for failed operations

### **Database Optimization**
- **Connection Pooling**: Reuse database connections
- **Indexing**: Optimize database queries
- **Caching**: Redis caching for frequently accessed data

### **Monitoring**
- **Metrics Collection**: Track performance metrics
- **Alerting**: Set up alerts for failures
- **Scaling**: Horizontal scaling with load balancers

## 🔮 **Future Enhancements**

### **Planned Features**
- **Real-time Dashboard**: Web-based management interface
- **Advanced Conflict Resolution**: ML-based conflict resolution
- **Multi-tenant Support**: Support for multiple organizations
- **Data Validation**: Schema validation and data quality checks
- **Backup & Recovery**: Automated backup and recovery procedures

### **Technical Improvements**
- **Microservices Architecture**: Split into smaller services
- **Event Sourcing**: Event-driven architecture
- **CQRS**: Command Query Responsibility Segregation
- **GraphQL API**: Modern API interface

## 📚 **Documentation**

- **API Documentation**: Available at `/docs` endpoint
- **Configuration Guide**: See `config/` directory
- **Deployment Guide**: See `docs/deployment.md`
- **Troubleshooting Guide**: See `docs/troubleshooting.md`

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 **Support**

- **Issues**: Create an issue on GitHub
- **Documentation**: Check the docs directory
- **Community**: Join our Discord server

---

**Built with ❤️ for seamless Frappe-Supabase synchronization**
