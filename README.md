# AudioBook Converter App

A cross-platform mobile application that converts PDF and EPUB books into high-quality audiobooks using AI text processing and text-to-speech technology.

## 🚀 Features

### Phase 1 (MVP)
- ✅ PDF and EPUB file import
- ✅ Text extraction and cleaning
- ✅ Text-to-speech conversion using Coqui TTS
- ✅ MP3 audio generation
- ✅ Basic audio playback

### Phase 2 (Enhanced)
- 🔄 AI text processing with Google Gemini
- 🔄 Multiple voice options
- 🔄 Chapter detection and splitting
- 🔄 Batch processing
- 🔄 Cloud storage integration

## 🛠 Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL
- **Caching**: Redis
- **TTS Engine**: Coqui TTS
- **LLM**: Google Gemini API
- **Storage**: Amazon S3 (coming soon)

### Frontend
- **Mobile App**: React Native
- **Cross-platform**: iOS & Android

### AI Services
- **Text Processing**: Google Gemini Pro
- **Text-to-Speech**: Coqui TTS (Open Source)

## 📁 Project Structure

```
audiobook/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Core functionality
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── utils/          # Utilities
│   ├── requirements.txt
│   └── main.py
├── mobile/                 # React Native app
│   ├── src/
│   │   ├── components/
│   │   ├── screens/
│   │   ├── services/
│   │   └── utils/
│   ├── package.json
│   └── App.js
├── docker-compose.yml      # Local development setup
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- PostgreSQL
- Redis
- Docker (optional)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Mobile App Setup
```bash
cd mobile
npm install
npx react-native run-android  # or run-ios
```

### Database Setup
```bash
# Create PostgreSQL database
createdb audiobook_db

# Run migrations
alembic upgrade head
```

## 🔧 Configuration

Create `.env` files in both `backend/` and `mobile/` directories:

### Backend `.env`
```
DATABASE_URL=postgresql://user:password@localhost/audiobook_db
REDIS_URL=redis://localhost:6379
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=your_secret_key
```

### Mobile `.env`
```
API_BASE_URL=http://localhost:8000
```

## 📝 API Documentation

Once the backend is running, visit:
- API Documentation: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Mobile tests
cd mobile
npm test
```

## 📊 Cost Optimization

This project uses cost-effective alternatives:
- **Coqui TTS**: Free, open-source TTS (vs ElevenLabs $15-30/million chars)
- **Google Gemini**: $0.50/million tokens (vs OpenAI $30-60/million tokens)
- **Self-hosted processing**: Reduces API costs by 70-80%

## 🚀 Deployment

### Backend (FastAPI)
- Deploy to AWS Lambda, Google Cloud Run, or similar
- Use managed PostgreSQL and Redis services

### Mobile App
- Build and deploy to App Store and Google Play Store

## 📋 Roadmap

- [ ] Basic MVP implementation
- [ ] AI text enhancement
- [ ] Voice customization
- [ ] Cloud storage integration
- [ ] Offline mode
- [ ] Social features

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 