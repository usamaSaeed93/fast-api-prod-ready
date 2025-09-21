# Project structure overview
fastapi-demo/
├── app/                          # Main application package
│   ├── __init__.py              # Package initialization
│   ├── config.py                # Configuration settings
│   ├── database.py              # Database connection and session
│   ├── models.py                # SQLAlchemy models
│   ├── schemas.py               # Pydantic schemas
│   ├── auth.py                  # Authentication and JWT handling
│   ├── services.py              # Business logic services
│   ├── rabbitmq.py              # RabbitMQ client
│   ├── background_jobs.py       # Background job processing
│   ├── email_service.py         # Email service
│   └── routers/                 # API route modules
│       └── auth.py              # Authentication routes
├── alembic/                     # Database migrations
│   ├── versions/                # Migration files
│   ├── env.py                   # Alembic environment
│   └── script.py.mako           # Migration template
├── tests/                       # Test files
│   └── test_api.py              # API tests
├── .github/                     # GitHub Actions
│   └── workflows/
│       └── ci.yml               # CI/CD pipeline
├── main.py                      # FastAPI application entry point
├── worker.py                    # Background job worker
├── test_api.py                  # API testing script
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── Dockerfile                   # Main application Docker image
├── Dockerfile.worker            # Worker Docker image
├── docker-compose.yml           # Development Docker Compose
├── docker-compose.prod.yml      # Production Docker Compose
├── nginx.conf                   # Nginx configuration
├── alembic.ini                  # Alembic configuration
├── .pre-commit-config.yaml      # Pre-commit hooks
├── .gitignore                   # Git ignore patterns
├── env.example                  # Environment variables template
├── Makefile                     # Development commands
├── start-dev.sh                 # Development startup script
├── start-prod.sh                # Production startup script
└── README.md                    # Project documentation
