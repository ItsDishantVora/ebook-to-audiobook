# AudioBook Converter - Development Guide

## 🏗️ Architecture Overview

This project is built using a modern tech stack optimized for cost-effectiveness and performance:

### Backend Stack
- **FastAPI** (Python) - High-performance async API framework
- **PostgreSQL** - Reliable database for book metadata and user data
- **Redis** - Caching and background job queue
- **Coqui TTS** - Open-source text-to-speech (saves 70-80% vs ElevenLabs)
- **Google Gemini** - Cost-effective AI text processing (80% cheaper than GPT-4)

### Frontend Stack
- **React Native** - Cross-platform mobile development
- **TypeScript** - Type safety and better development experience
- **React Navigation** - Navigation framework
- **React Query** - Server state management

## 🛠️ Development Setup

### Prerequisites

1. **Python 3.9+**
   ```bash
   python3 --version
   ```

2. **Node.js 18+**
   ```bash
   node --version
   npm --version
   ```

3. **PostgreSQL** (or use Docker)
   ```bash
   psql --version
   ```

4. **Redis** (or use Docker)
   ```bash
   redis-cli --version
   ```

5. **React Native CLI** (for mobile development)
   ```bash
   npm install -g react-native-cli
   ```

### Quick Start

1. **Clone and setup the project:**
   ```bash
   git clone <your-repo-url>
   cd audiobook
   ./setup.sh
   ```

2. **Configure environment variables:**
   - Copy `backend/env.example` to `backend/.env`
   - Add your Gemini API key from [Google AI Studio](https://ai.google.dev/)

3. **Start with Docker (Recommended):**
   ```bash
   docker-compose up -d
   ```

4. **Or start manually:**
   ```bash
   # Terminal 1: Start backend
   cd backend
   source venv/bin/activate
   uvicorn main:app --reload
   
   # Terminal 2: Start mobile app
   cd mobile
   npm start
   ```

## 📁 Project Structure

```
audiobook/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API routes
│   │   │   └── endpoints/     # Individual endpoint files
│   │   ├── core/              # Core configuration
│   │   │   ├── config.py      # Settings and configuration
│   │   │   ├── database.py    # Database connection
│   │   │   └── exceptions.py  # Custom exceptions
│   │   ├── models/            # SQLAlchemy models
│   │   │   ├── user.py        # User model
│   │   │   ├── book.py        # Book model
│   │   │   └── conversion_job.py # Background job tracking
│   │   ├── services/          # Business logic
│   │   │   ├── file_processor.py  # PDF/EPUB processing
│   │   │   ├── gemini_service.py  # AI text enhancement
│   │   │   ├── tts_service.py     # Coqui TTS integration
│   │   │   └── text_processor.py # Text cleaning utilities
│   │   └── utils/             # Utility functions
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Docker configuration
│   └── main.py               # FastAPI app entry point
├── mobile/                    # React Native app
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── screens/          # Screen components
│   │   ├── navigation/       # Navigation setup
│   │   ├── services/         # API services
│   │   ├── context/          # React context providers
│   │   └── utils/            # Utility functions
│   ├── package.json          # Node.js dependencies
│   └── App.tsx               # Main app component
├── docker-compose.yml        # Docker services setup
├── setup.sh                  # Automated setup script
└── README.md                 # Project documentation
```

## 🔧 Development Workflow

### Backend Development

1. **Create new API endpoints:**
   ```python
   # backend/app/api/endpoints/new_feature.py
   from fastapi import APIRouter
   
   router = APIRouter()
   
   @router.get("/new-endpoint")
   async def new_endpoint():
       return {"message": "Hello World"}
   ```

2. **Add database models:**
   ```python
   # backend/app/models/new_model.py
   from sqlalchemy import Column, String, DateTime
   from app.core.database import Base
   
   class NewModel(Base):
       __tablename__ = "new_table"
       id = Column(String, primary_key=True)
       # ... other fields
   ```

3. **Run database migrations:**
   ```bash
   cd backend
   alembic revision --autogenerate -m "Add new model"
   alembic upgrade head
   ```

### Mobile Development

1. **Start development server:**
   ```bash
   cd mobile
   npm start
   ```

2. **Run on Android:**
   ```bash
   npm run android
   ```

3. **Run on iOS:**
   ```bash
   npm run ios
   ```

### Testing

1. **Backend tests:**
   ```bash
   cd backend
   pytest
   ```

2. **Mobile tests:**
   ```bash
   cd mobile
   npm test
   ```

## 🚀 Deployment

### Backend Deployment

1. **Build Docker image:**
   ```bash
   docker build -t audiobook-backend ./backend
   ```

2. **Deploy to cloud:**
   - AWS ECS/Fargate
   - Google Cloud Run
   - Azure Container Instances

### Mobile App Deployment

1. **Android:**
   ```bash
   cd mobile
   npm run build:android
   # Upload APK to Google Play Console
   ```

2. **iOS:**
   ```bash
   cd mobile
   npm run build:ios
   # Upload to App Store Connect
   ```

## 🧪 Key Features Implementation

### Text-to-Speech Conversion

The TTS service uses Coqui TTS for cost-effective, high-quality speech synthesis:

```python
# Example usage
from app.services import TTSService

tts = TTSService()
result = await tts.convert_text_to_audio(
    text="Your book text here",
    output_path="/path/to/output.mp3",
    voice="default"
)
```

### AI Text Enhancement

Gemini API is used for intelligent text processing:

```python
# Example usage
from app.services import GeminiService

gemini = GeminiService()
enhanced_text = await gemini.enhance_text_for_audiobook(
    raw_text="Extracted book text",
    book_metadata={"title": "Book Title", "author": "Author"}
)
```

### File Processing

Support for PDF and EPUB files:

```python
# Example usage
from app.services import FileProcessor

processor = FileProcessor()
result = await processor.extract_text_from_file(
    file_path="/path/to/book.pdf",
    file_type="pdf"
)
```

## 📊 Cost Optimization

This project uses cost-effective alternatives to expensive AI services:

| Service | Traditional Option | Our Choice | Savings |
|---------|-------------------|------------|---------|
| TTS | ElevenLabs ($15-30/M chars) | Coqui TTS (Free) | 100% |
| LLM | OpenAI GPT-4 ($30-60/M tokens) | Gemini ($0.50/M tokens) | 80-98% |
| Storage | Premium cloud storage | S3 Standard | 60-80% |

**Estimated monthly costs for 1000 active users:**
- **Traditional stack**: $1,200-2,000/month
- **Our optimized stack**: $400-600/month
- **Savings**: 60-70% reduction in operating costs

## 🔒 Security Considerations

1. **Environment Variables:**
   - Never commit API keys to version control
   - Use `.env` files for local development
   - Use secrets management in production

2. **File Upload Security:**
   - Validate file types and sizes
   - Scan uploaded files for malware
   - Use secure file storage

3. **API Security:**
   - Implement rate limiting
   - Use authentication and authorization
   - Validate all input data

## 📈 Performance Optimization

1. **Backend:**
   - Use async/await for I/O operations
   - Implement Redis caching
   - Use background jobs for heavy processing

2. **Mobile:**
   - Lazy load screens and components
   - Optimize images and assets
   - Use React Query for efficient data fetching

## 🐛 Troubleshooting

### Common Issues

1. **TTS Model Download Fails:**
   ```bash
   # Manually download and cache the model
   python -c "from TTS.api import TTS; TTS('tts_models/en/ljspeech/tacotron2-DDC')"
   ```

2. **Database Connection Issues:**
   ```bash
   # Check PostgreSQL is running
   docker-compose ps postgres
   
   # Reset database
   docker-compose down -v
   docker-compose up -d postgres
   ```

3. **Mobile App Won't Build:**
   ```bash
   # Clean and reinstall dependencies
   cd mobile
   rm -rf node_modules
   npm install
   
   # For React Native specific issues
   npx react-native clean
   ```

4. **Gemini API Errors:**
   - Verify API key is correct
   - Check quota limits
   - Ensure billing is enabled

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Native Documentation](https://reactnative.dev/)
- [Coqui TTS Documentation](https://docs.coqui.ai/)
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes and test them
4. Commit your changes: `git commit -am 'Add new feature'`
5. Push to the branch: `git push origin feature/new-feature`
6. Create a Pull Request

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details. 