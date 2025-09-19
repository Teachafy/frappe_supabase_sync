# 🚀 Production Deployment Guide

## Overview
This guide covers everything you need to deploy and configure the Frappe-Supabase sync system in production.

## 1. Service Deployment

### Option A: Docker Deployment (Recommended)
```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f sync-service
```

### Option B: Direct Python Deployment
```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Start the service
python main.py
```

## 2. Webhook Configuration

### 2.1 Frappe Webhook Setup

**Frappe Webhook Configuration:**
- **URL**: `https://your-domain.com/webhooks/frappe`
- **Method**: POST
- **Events**: Document Events (Insert, Update, Delete)
- **Doctypes**: Employee, Task
- **Secret**: Use the `WEBHOOK_SECRET` from your .env file

**Steps:**
1. Go to your Frappe instance: `https://stonemart.frappe.cloud`
2. Navigate to: **Setup → Integrations → Webhooks**
3. Click **New Webhook**

**For Employee Doctype (3 separate webhooks required):**

4. **Employee Insert Webhook:**
   - **Webhook ID**: `frappe_sync_employee_insert`
   - **Request URL**: `https://your-domain.com/webhooks/frappe`
   - **Request Method**: POST
   - **Request Headers**: `{"Content-Type": "application/json", "X-Frappe-Signature": "HAPPY"}`
   - **Webhook Events**: Document Events → Employee → After Insert
   - **Document Types**: Employee
   - **Enabled**: Yes

5. **Employee Update Webhook:**
   - **Webhook ID**: `frappe_sync_employee_update`
   - **Request URL**: `https://your-domain.com/webhooks/frappe`
   - **Request Method**: POST
   - **Request Headers**: `{"Content-Type": "application/json", "X-Frappe-Signature": "HAPPY"}`
   - **Webhook Events**: Document Events → Employee → After Update
   - **Document Types**: Employee
   - **Enabled**: Yes

6. **Employee Delete Webhook:**
   - **Webhook ID**: `frappe_sync_employee_delete`
   - **Request URL**: `https://your-domain.com/webhooks/frappe`
   - **Request Method**: POST
   - **Request Headers**: `{"Content-Type": "application/json", "X-Frappe-Signature": "HAPPY"}`
   - **Webhook Events**: Document Events → Employee → After Delete
   - **Document Types**: Employee
   - **Enabled**: Yes

**For Task Doctype (3 separate webhooks required):**

7. **Task Insert Webhook:**
   - **Webhook ID**: `frappe_sync_task_insert`
   - **Request URL**: `https://your-domain.com/webhooks/frappe`
   - **Request Method**: POST
   - **Request Headers**: `{"Content-Type": "application/json", "X-Frappe-Signature": "HAPPY"}`
   - **Webhook Events**: Document Events → Task → After Insert
   - **Document Types**: Task
   - **Enabled**: Yes

8. **Task Update Webhook:**
   - **Webhook ID**: `frappe_sync_task_update`
   - **Request URL**: `https://your-domain.com/webhooks/frappe`
   - **Request Method**: POST
   - **Request Headers**: `{"Content-Type": "application/json", "X-Frappe-Signature": "HAPPY"}`
   - **Webhook Events**: Document Events → Task → After Update
   - **Document Types**: Task
   - **Enabled**: Yes

9. **Task Delete Webhook:**
   - **Webhook ID**: `frappe_sync_task_delete`
   - **Request URL**: `https://your-domain.com/webhooks/frappe`
   - **Request Method**: POST
   - **Request Headers**: `{"Content-Type": "application/json", "X-Frappe-Signature": "HAPPY"}`
   - **Webhook Events**: Document Events → Task → After Delete
   - **Document Types**: Task
   - **Enabled**: Yes

### 2.2 Supabase Webhook Setup

**Supabase Webhook Configuration:**
- **URL**: `https://your-domain.com/webhooks/supabase`
- **Method**: POST
- **Tables**: users, tasks
- **Secret**: Use the `WEBHOOK_SECRET` from your .env file

**Steps:**
1. Go to your Supabase project dashboard
2. Navigate to: **Database → Webhooks**
3. Click **Create a new hook**
4. Configure for `users` table:
   - **Name**: `supabase_sync_users`
   - **Table**: `users`
   - **Events**: Insert, Update, Delete
   - **Type**: HTTP Request
   - **Method**: POST
   - **URL**: `https://your-domain.com/webhooks/supabase`
   - **Headers**: `{"Content-Type": "application/json", "X-Supabase-Signature": "your_webhook_secret"}`
   - **Enabled**: Yes

5. Repeat for `tasks` table:
   - **Name**: `supabase_sync_tasks`
   - **Table**: `tasks`

## 3. Environment Configuration

### 3.1 Production Environment Variables

Update your `.env` file with production values:

```env
# Production URLs
FRAPPE_URL=https://stonemart.frappe.cloud
SUPABASE_URL=https://robin-supabase.m9ljtu.easypanel.host

# API Credentials (already configured)
FRAPPE_API_KEY=e498231aca3644e
FRAPPE_API_SECRET=83c57f0aab53805
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Webhook Configuration
WEBHOOK_SECRET=your_secure_webhook_secret
WEBHOOK_TIMEOUT=30

# Production Settings
LOG_LEVEL=INFO
SYNC_BATCH_SIZE=50
SYNC_RETRY_ATTEMPTS=5
SYNC_RETRY_DELAY=10
CONFLICT_RESOLUTION_STRATEGY=last_modified_wins

# Database (if using external database)
DATABASE_URL=postgresql://user:password@host:port/database

# Redis (if using external Redis)
REDIS_URL=redis://your-redis-host:6379/0
```

### 3.2 Security Configuration

1. **Generate a secure webhook secret**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update webhook secret** in both Frappe and Supabase webhook configurations

3. **Enable HTTPS** for your sync service domain

## 4. Service Endpoints

### 4.1 Webhook Endpoints

**Frappe Webhook Handler:**
- **URL**: `POST /webhooks/frappe`
- **Purpose**: Receives events from Frappe (Employee, Task changes)
- **Authentication**: Webhook secret validation
- **Payload**: Frappe document event data

**Supabase Webhook Handler:**
- **URL**: `POST /webhooks/supabase`
- **Purpose**: Receives events from Supabase (users, tasks changes)
- **Authentication**: Webhook secret validation
- **Payload**: Supabase table change data

### 4.2 API Endpoints

**Health Check:**
- **URL**: `GET /health`
- **Purpose**: Service health monitoring

**Sync Status:**
- **URL**: `GET /sync/status`
- **Purpose**: View sync operations status

**Manual Sync:**
- **URL**: `POST /sync/manual`
- **Purpose**: Trigger manual sync operations

**Schema Discovery:**
- **URL**: `GET /api/schema/discover`
- **Purpose**: Discover and map schemas

## 5. Monitoring & Logging

### 5.1 Log Monitoring
```bash
# View service logs
docker-compose logs -f sync-service

# Or if running directly
tail -f sync_service.log
```

### 5.2 Metrics Dashboard
- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3000`
- **Default credentials**: admin/admin

### 5.3 Health Checks
```bash
# Check service health
curl http://localhost:8000/health

# Check sync status
curl http://localhost:8000/sync/status
```

## 6. Testing the Setup

### 6.1 Test Webhook Endpoints
```bash
# Test Frappe webhook
curl -X POST http://localhost:8000/webhooks/frappe \
  -H "Content-Type: application/json" \
  -H "X-Frappe-Signature: HAPPY" \
  -d '{"doctype": "Employee", "name": "HR-EMP-00001", "action": "insert"}'

# Test Supabase webhook
curl -X POST http://localhost:8000/webhooks/supabase \
  -H "Content-Type: application/json" \
  -H "X-Supabase-Signature: your_webhook_secret" \
  -d '{"table": "users", "id": 1, "action": "insert"}'
```

### 6.2 Test Data Sync
1. Create a new Employee in Frappe
2. Verify it appears in Supabase users table
3. Update the record in Supabase
4. Verify changes appear in Frappe

## 7. Production Considerations

### 7.1 Scaling
- Use multiple sync service instances behind a load balancer
- Configure Redis for distributed task queue
- Use external PostgreSQL for persistent storage

### 7.2 Security
- Enable HTTPS with valid SSL certificates
- Use strong webhook secrets
- Implement rate limiting
- Monitor for suspicious activity

### 7.3 Backup & Recovery
- Regular database backups
- Webhook event logging
- Sync operation audit trails

## 8. Troubleshooting

### 8.1 Common Issues
- **Webhook not triggering**: Check URL accessibility and secret
- **Sync failures**: Check API credentials and network connectivity
- **Data conflicts**: Review conflict resolution strategy

### 8.2 Debug Commands
```bash
# Check service status
docker-compose ps

# View detailed logs
docker-compose logs --tail=100 sync-service

# Test API connectivity
curl -X GET "https://stonemart.frappe.cloud/api/method/frappe.client.get_list?doctype=Employee&limit_page_length=1" \
  -H "Authorization: token e498231aca3644e:83c57f0aab53805"
```

## 9. Next Steps After Deployment

1. **Monitor the first few sync operations**
2. **Set up alerting for sync failures**
3. **Configure backup strategies**
4. **Document any custom mappings**
5. **Train your team on the sync system**

## 10. Support & Maintenance

- **Logs**: Check service logs regularly
- **Metrics**: Monitor sync performance
- **Updates**: Keep dependencies updated
- **Backups**: Regular data backups
- **Testing**: Periodic sync testing

---

## Quick Start Commands

```bash
# 1. Start the service
python main.py

# 2. Test health
curl http://localhost:8000/health

# 3. Configure webhooks (see sections 2.1 and 2.2)

# 4. Test sync
curl -X POST http://localhost:8000/sync/manual
```

Your sync system is now ready for production! 🎉
