# CSU Global Transcript Evaluator

An AI-powered system for evaluating transfer credits from academic transcripts for CSU Global.

## Features

- Extract course data from transcripts using Google's Gemini AI
- Apply transfer credit rules based on CSU Global policies
- Generate detailed evaluation reports
- Interactive UI for reviewing and managing evaluations
- Role-based access control
- Comprehensive audit logging
- API rate limiting and security
- Performance optimization through caching

## System Components

### Core Modules

- `confidence_scorer.py`: Confidence scoring for data extraction
- `evaluator.py`: Transfer credit evaluation rules
- `models.py`: Data structures for students, courses, and institutions
- `display.py`: UI and report generation
- `parsers.py`: Data parsing and normalization
- `processors.py`: Transcript processing workflow
- `gemini_client.py`: Google Gemini AI integration

### Security & Performance

- `auth.py`: Role-based access control system
- `rules_engine.py`: Business rules engine
- `audit.py`: Comprehensive audit logging
- `rate_limit.py`: API rate limiting
- `cache.py`: Performance optimization

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/csug_transcript_estimator.git
cd csug_transcript_estimator
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

### Environment Variables

- `GEMINI_API_KEY`: Google Gemini API key
- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `REDIS_URL`: Redis connection URL
- `DATABASE_URL`: Database connection URL
- `LOG_LEVEL`: Logging level (DEBUG, INFO, etc.)

### Role-Based Access

Three user roles are available:
- **Enrollment**: Basic view access
- **TES**: Transfer evaluation specialist with edit access
- **Admin**: Full system access

## Usage

1. Start the application:
```bash
streamlit run src/app.py
```

2. Access the web interface at `http://localhost:8501`

3. Log in with your credentials

4. Upload transcripts for evaluation

## API Documentation

### Rate Limits

- Default: 100 requests per hour
- Authenticated: 1000 requests per hour
- Burst: 50 requests per minute

### Endpoints

- `POST /api/v1/evaluate`: Submit transcript for evaluation
- `GET /api/v1/results/{id}`: Get evaluation results
- `PUT /api/v1/review/{id}`: Update evaluation
- `GET /api/v1/reports`: Generate reports

## Security Features

1. **Role-Based Access Control**
   - Granular permissions system
   - JWT-based authentication
   - Session management

2. **API Protection**
   - Rate limiting
   - Request validation
   - CORS configuration

3. **Audit Logging**
   - User activity tracking
   - Data change history
   - Security event logging

4. **Data Security**
   - Encryption at rest
   - Secure credential storage
   - Input sanitization

## Performance Optimization

1. **Caching System**
   - Redis-based caching
   - In-memory fallback
   - Configurable TTL

2. **Rate Limiting**
   - Token bucket algorithm
   - Distributed rate limiting
   - Custom limits per endpoint

## Development

### Testing

Run tests:
```bash
pytest
```

Generate coverage report:
```bash
pytest --cov=src tests/
```

### Code Style

Format code:
```bash
black src/
```

Run linter:
```bash
flake8 src/
```

Type checking:
```bash
mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 