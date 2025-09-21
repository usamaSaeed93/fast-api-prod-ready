# 🚀 FastAPI Enterprise Demo

A comprehensive, production-ready FastAPI application showcasing enterprise-grade Python development practices with advanced authentication, background job processing, and microservices architecture.

## ✨ Key Features

### 🔐 **Advanced Authentication & Authorization**
- JWT-based authentication with access & refresh tokens
- Role-based access control (RBAC)
- Password strength validation
- Account lockout protection
- Session management with Redis
- Comprehensive audit logging

### 🐰 **Enterprise Message Queue Integration**
- RabbitMQ integration with topic exchanges
- Priority-based job queuing
- Retry mechanisms with exponential backoff
- Dead letter queue handling
- Message persistence and durability

### 📧 **Background Job Processing**
- Asynchronous email processing
- Data processing pipelines
- System cleanup tasks
- Notification services
- Job status tracking and monitoring
- Real-time job statistics

### 🏗️ **Enterprise Architecture**
- Clean Architecture with separation of concerns
- Dependency injection patterns
- Service layer abstraction
- Repository pattern implementation
- Domain-driven design principles

### 📊 **Comprehensive Monitoring & Observability**
- Prometheus metrics integration
- Structured JSON logging
- Health check endpoints
- Performance monitoring
- System resource tracking
- Request tracing with correlation IDs

### 🔒 **Security & Compliance**
- Input validation with Pydantic
- SQL injection protection
- CORS configuration
- Security headers middleware
- Rate limiting
- Audit trail for all operations

### 🐳 **Production-Ready Deployment**
- Docker containerization
- Docker Compose orchestration
- Nginx reverse proxy
- Environment-based configuration
- Health checks and auto-restart
- Horizontal scaling support

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Enterprise Demo                  │
├─────────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                           │
│  ├── Authentication & Authorization                            │
│  ├── Background Job Management                                 │
│  ├── User Management                                           │
│  └── System Monitoring                                         │
├─────────────────────────────────────────────────────────────────┤
│  Service Layer                                                 │
│  ├── UserService                                               │
│  ├── JobService                                                │
│  ├── AuditService                                              │
│  └── EmailService                                              │
├─────────────────────────────────────────────────────────────────┤
│  Core Layer                                                    │
│  ├── Authentication (JWT)                                      │
│  ├── Database (SQLAlchemy)                                     │
│  ├── Cache (Redis)                                             │
│  ├── Message Queue (RabbitMQ)                                  │
│  └── Monitoring (Prometheus)                                   │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure                                                │
│  ├── PostgreSQL Database                                       │
│  ├── Redis Cache                                               │
│  ├── RabbitMQ Message Broker                                   │
│  └── Nginx Load Balancer                                       │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Git

### 🐳 **Docker Deployment (Recommended)**

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd fastapi-enterprise-demo
   cp env.production .env
   # Edit .env with your configuration
   ```

2. **Start All Services**
   ```bash
   make docker-up
   ```

3. **Access the Application**
   - **API**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **RabbitMQ Management**: http://localhost:15672 (guest/guest)
   - **Prometheus Metrics**: http://localhost:8000/api/v1/metrics

### 🛠️ **Local Development**

1. **Install Dependencies**
   ```bash
   make dev-install
   ```

2. **Setup Environment**
   ```bash
   make setup-dev
   ```

3. **Start Services**
   ```bash
   make dev
   # In another terminal
   make worker
   ```

## 📖 API Documentation

### **Authentication Endpoints**

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/auth/register` | Register new user | ❌ |
| `POST` | `/api/v1/auth/login` | User login | ❌ |
| `POST` | `/api/v1/auth/refresh` | Refresh access token | ❌ |
| `POST` | `/api/v1/auth/logout` | User logout | ✅ |
| `GET` | `/api/v1/auth/me` | Get current user | ✅ |
| `PUT` | `/api/v1/auth/me` | Update current user | ✅ |
| `POST` | `/api/v1/auth/change-password` | Change password | ✅ |
| `GET` | `/api/v1/auth/users` | List users (Admin) | ✅ Admin |
| `GET` | `/api/v1/auth/users/{id}` | Get user by ID (Admin) | ✅ Admin |
| `PUT` | `/api/v1/auth/users/{id}` | Update user (Admin) | ✅ Admin |
| `DELETE` | `/api/v1/auth/users/{id}` | Deactivate user (Admin) | ✅ Admin |

### **Background Jobs**

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/jobs` | Create background job | ✅ |
| `GET` | `/api/v1/jobs` | List jobs | ✅ |
| `GET` | `/api/v1/jobs/{job_id}` | Get job details | ✅ |
| `GET` | `/api/v1/jobs/statistics` | Job statistics (Admin) | ✅ Admin |
| `POST` | `/api/v1/send-email` | Send email (queued) | ✅ |
| `POST` | `/api/v1/send-notification` | Send notification | ✅ |
| `POST` | `/api/v1/process-data` | Process data | ✅ |
| `POST` | `/api/v1/cleanup` | System cleanup (Admin) | ✅ Admin |

### **System & Monitoring**

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/api/v1/health` | Health check | ❌ |
| `GET` | `/api/v1/metrics` | Prometheus metrics | ❌ |
| `GET` | `/api/v1/info` | System information | ❌ |
| `GET` | `/` | API information | ❌ |

## 🔧 Configuration

### **Environment Variables**

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/fastapi_demo
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Security
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
PASSWORD_MIN_LENGTH=8
MAX_LOGIN_ATTEMPTS=5

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_EXCHANGE=fastapi_demo
RABBITMQ_MAX_RETRIES=3

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_DEFAULT_TTL=3600

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Monitoring
ENABLE_METRICS=true
LOG_FORMAT=json
```

## 🧪 Testing

### **Run Tests**
```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# With coverage
make test-cov

# Watch mode
make test-watch
```

### **Test Categories**
- **Unit Tests**: Service layer, utilities, core functionality
- **Integration Tests**: API endpoints, database operations
- **Authentication Tests**: Login, registration, token validation
- **Job Tests**: Background job creation, processing, monitoring

## 🔍 Code Quality

### **Linting & Formatting**
```bash
# Format code
make format

# Check formatting
make format-check

# Run linting
make lint

# Run all checks
make check
```

### **Quality Tools**
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pre-commit**: Git hooks

## 📊 Monitoring & Observability

### **Metrics**
- HTTP request metrics (count, duration, status codes)
- Background job metrics (created, completed, failed)
- System metrics (memory, CPU, database connections)
- Cache metrics (hits, misses, operations)

### **Logging**
- Structured JSON logging
- Request correlation IDs
- Performance timing
- Error tracking with stack traces
- Audit trail for all operations

### **Health Checks**
- Database connectivity
- Redis connectivity
- RabbitMQ connectivity
- System resource usage
- Service uptime

## 🚀 Production Deployment

### **Docker Production**
```bash
# Build and deploy
make docker-build
make docker-up

# Scale workers
make scale-worker REPLICAS=3

# Monitor
make monitor
make health-check
```

### **Environment Setup**
1. **Database**: Use managed PostgreSQL service
2. **Cache**: Use managed Redis service
3. **Message Queue**: Use managed RabbitMQ service
4. **Load Balancer**: Configure Nginx with SSL
5. **Monitoring**: Set up Prometheus + Grafana
6. **Logging**: Centralized logging with ELK stack

## 🛠️ Development

### **Available Commands**
```bash
make help                 # Show all available commands
make dev                  # Start development server
make worker               # Start background worker
make migrate              # Run database migrations
make migration MSG="..."  # Create new migration
make clean                # Clean temporary files
make docs                 # Generate API documentation
```

### **Database Migrations**
```bash
# Create migration
make migration MSG="Add user preferences table"

# Apply migrations
make migrate

# Check migration status
alembic current
```

## 📈 Performance

### **Optimization Features**
- Database connection pooling
- Redis caching with TTL
- Async/await throughout
- Background job processing
- Request/response compression
- Static file serving

### **Load Testing**
```bash
# Run load tests
make load-test

# Performance tests
make performance
```

## 🔒 Security Features

- **JWT Tokens**: Secure token-based authentication
- **Password Hashing**: Bcrypt with salt
- **Input Validation**: Pydantic model validation
- **SQL Injection Protection**: SQLAlchemy ORM
- **CORS Protection**: Configurable CORS middleware
- **Rate Limiting**: Request rate limiting
- **Security Headers**: XSS, CSRF protection
- **Audit Logging**: Complete operation tracking

## 📚 API Examples

### **Register User**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "SecurePassword123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### **Login**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "SecurePassword123"
  }'
```

### **Create Background Job**
```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "send_email",
    "payload": {
      "to_email": "recipient@example.com",
      "subject": "Test Email",
      "body": "This is a test email from FastAPI Enterprise Demo"
    },
    "priority": 1
  }'
```

### **Send Email**
```bash
curl -X POST "http://localhost:8000/api/v1/send-email" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to_email": "recipient@example.com",
    "subject": "Welcome to FastAPI Enterprise Demo",
    "body": "<h1>Welcome!</h1><p>Thank you for using our service.</p>",
    "is_html": true
  }'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run quality checks (`make check`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check `/docs` endpoint for interactive API docs
- **Health Check**: Monitor `/api/v1/health` for system status
- **Issues**: Create an issue in the repository
- **Discussions**: Use GitHub Discussions for questions

---

**Built with ❤️ using FastAPI, RabbitMQ, PostgreSQL, Redis, and modern Python practices**

*Perfect for technical interviews, portfolio demonstrations, and enterprise application templates*"# fast-api-prod-ready" 
