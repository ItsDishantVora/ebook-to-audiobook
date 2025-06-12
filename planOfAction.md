# Audiobook Converter App - Plan of Action

## 🎯 Project Overview

Build a cost-effective, fast audiobook converter that transforms ebooks (EPUB, PDF) into single MP3 audiobook files using:
- **Gemini LLM** for text processing and optimization
- **Async processing** for speed
- **TTS (Text-to-Speech)** for audio conversion
- **Smart chunking** for cost optimization

## 🏗️ Architecture Overview

```
Input (EPUB/PDF) → Text Extraction → Text Processing (Gemini) → TTS Conversion → Audio Merging → Output (MP3)
```

## 📋 Phase 1: Foundation & Setup

### 1.1 Project Structure
```
audiobook/
├── app.py                 # Main FastAPI/Streamlit app
├── core/
│   ├── __init__.py
│   ├── text_extractor.py  # EPUB/PDF text extraction
│   ├── text_processor.py  # Gemini-based text processing
│   ├── tts_converter.py   # Text-to-speech conversion
│   ├── audio_merger.py    # Combine audio chunks
│   └── utils.py           # Helper functions
├── config/
│   ├── __init__.py
│   └── settings.py        # Configuration management
├── templates/             # UI templates (if using web interface)
├── static/               # Static files
├── temp/                 # Temporary files
├── output/               # Generated audiobooks
├── requirements.txt      # Dependencies
├── .env                 # Environment variables
├── planOfAction.md      # This file
└── README.md            # Project documentation
```

### 1.2 Key Dependencies
- **Text Extraction**: `PyPDF2`, `pdfplumber`, `ebooklib`, `beautifulsoup4`
- **LLM Integration**: `google-generativeai`
- **TTS**: `gTTS` (Google TTS), `pyttsx3`, or `edge-tts` (free alternatives)
- **Audio Processing**: `pydub`, `ffmpeg-python`
- **Async**: `asyncio`, `aiofiles`, `httpx`
- **Web Framework**: `fastapi`, `streamlit` (choose one)
- **Other**: `python-dotenv`, `tqdm`

## 📋 Phase 2: Core Components Development

### 2.1 Text Extraction Module (`text_extractor.py`)
- **EPUB Support**: Use `ebooklib` to extract chapters and text
- **PDF Support**: Use `pdfplumber` for better text extraction
- **Features**:
  - Preserve chapter structure
  - Handle images/tables gracefully
  - Extract metadata (title, author, etc.)
  - Async processing for large files

### 2.2 Text Processing Module (`text_processor.py`)
- **Gemini Integration**: 
  - Clean and optimize text for TTS
  - Add proper punctuation and pauses
  - Break long sentences
  - Remove formatting artifacts
  - Handle special characters
- **Cost Optimization**:
  - Batch processing to reduce API calls
  - Smart chunking (max 30K characters per request)
  - Caching processed chunks
  - Rate limiting

### 2.3 TTS Conversion Module (`tts_converter.py`)
- **Multi-TTS Support**:
  - Primary: `edge-tts` (free, high quality)
  - Fallback: `gTTS` (Google TTS)
  - Advanced: `coqui-tts` (if local processing desired)
- **Features**:
  - Async audio generation
  - Multiple voice options
  - Speed and pitch control
  - Chapter-based processing
  - Progress tracking

### 2.4 Audio Merger Module (`audio_merger.py`)
- **Functionality**:
  - Combine multiple audio chunks
  - Add silence between chapters
  - Normalize audio levels
  - Add metadata to final MP3
  - Optimize file size

## 📋 Phase 3: User Interface

### 3.1 Web Interface Options
**Option A: Streamlit (Simpler)**
- Drag-and-drop file upload
- Progress bars
- Real-time logs
- Download link

**Option B: FastAPI + HTML (More Professional)**
- RESTful API
- WebSocket for real-time updates
- Better error handling
- Scalable

### 3.2 Features
- File upload (EPUB/PDF)
- Voice selection
- Speed adjustment
- Progress tracking
- Download management

## 📋 Phase 4: Optimization & Cost Management

### 4.1 Gemini Cost Optimization
- **Batching**: Process multiple chapters together
- **Caching**: Store processed text to avoid re-processing
- **Smart Chunking**: Optimize chunk sizes for API efficiency
- **Rate Limiting**: Prevent excessive API calls
- **Error Handling**: Graceful fallbacks

### 4.2 Performance Optimization
- **Async Processing**: Parallel text extraction and audio generation
- **Memory Management**: Stream processing for large files
- **Temporary File Cleanup**: Automatic cleanup of intermediate files
- **Progress Tracking**: Real-time feedback to users

## 📋 Phase 5: Advanced Features (Future)

### 5.1 Enhanced Processing
- **Voice Cloning**: Integration with advanced TTS models
- **Multi-language Support**: Automatic language detection
- **Chapter Detection**: Smart chapter boundary detection
- **Metadata Enhancement**: Rich metadata extraction

### 5.2 User Experience
- **Batch Processing**: Multiple books at once
- **Cloud Storage**: Integration with Google Drive/Dropbox
- **Mobile App**: React Native or Flutter app
- **API**: RESTful API for third-party integrations

## 🔧 Implementation Strategy

### Week 1: Foundation
1. Set up project structure
2. Implement basic text extraction (EPUB/PDF)
3. Set up Gemini integration
4. Basic TTS conversion

### Week 2: Core Features
1. Implement text processing with Gemini
2. Async audio generation
3. Audio merging functionality
4. Basic web interface

### Week 3: Optimization
1. Cost optimization for Gemini
2. Performance improvements
3. Error handling and logging
4. Testing and debugging

### Week 4: Polish & Deploy
1. UI/UX improvements
2. Documentation
3. Deployment setup
4. Final testing

## 💰 Cost Considerations

### Gemini API Costs
- **Free Tier**: 15 requests per minute, 1500 per day
- **Paid Tier**: $0.00025 per 1K characters (input), $0.00075 per 1K characters (output)
- **Optimization**: Average book ~300K characters → ~$0.30-0.50 per book (very cost-effective)

### Alternative TTS Options
- **edge-tts**: Free, high quality
- **gTTS**: Free, good quality
- **Azure/AWS TTS**: Paid but very high quality

## 🎯 Success Metrics

1. **Processing Speed**: < 5 minutes for average book (300 pages)
2. **Cost**: < $1 per audiobook conversion
3. **Quality**: Clear, properly paced audio
4. **User Experience**: Simple, intuitive interface
5. **Reliability**: 99%+ success rate

## 🚀 Getting Started

1. Review and approve this plan
2. Set up development environment
3. Start with Phase 1 implementation
4. Iterate and improve based on testing

---

*This plan will be updated as we progress through development* 