"""
Enhanced Audiobook Converter with Coqui TTS
Converts EPUB/PDF books to high-quality MP3 audiobooks using AI
"""

import streamlit as st
import asyncio
import os
import logging
from pathlib import Path
import tempfile
import zipfile
from datetime import datetime

# Core modules
from core.text_extractor import TextExtractor
from core.text_processor import TextProcessor
from core.tts_converter import TTSConverter
from core.audio_merger import AudioMerger
from config import settings

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

def main():
    st.set_page_config(
        page_title="🎧 Enhanced Audiobook Converter",
        page_icon="🎧",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better UI
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-box {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .quality-badge {
        background: #28a745;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
    }
    .cache-info {
        background: #f8f9fa;
        border-left: 4px solid #007bff;
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">🎧 Enhanced Audiobook Converter</h1>', unsafe_allow_html=True)
    st.markdown('<div class="feature-box">✨ Now with <strong>Coqui TTS</strong> for studio-quality voice synthesis! ✨</div>', unsafe_allow_html=True)
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # TTS Engine Selection
        st.subheader("🎙️ Voice Engine")
        
        # Check if Coqui TTS is available
        try:
            from TTS.api import TTS
            coqui_available = True
        except ImportError:
            coqui_available = False
        
        if coqui_available:
            st.success("✅ Coqui TTS Available (Highest Quality)")
            engine_options = ["coqui-xtts", "edge-tts", "gtts", "pyttsx3"]
            default_engine = "coqui-xtts"
        else:
            st.warning("⚠️ Coqui TTS not installed. Using fallback engines.")
            engine_options = ["edge-tts", "gtts", "pyttsx3"]
            default_engine = "edge-tts"
        
        selected_engine = st.selectbox(
            "Select TTS Engine:",
            engine_options,
            index=engine_options.index(default_engine),
            help="Coqui TTS provides the most natural voice quality"
        )
        
        # Voice Selection based on engine
        st.subheader("🗣️ Voice Selection")
        
        if selected_engine == "coqui-xtts":
            voice_options = {
                "tts_models/en/ljspeech/tacotron2-DDC": "📚 LJSpeech - Perfect for Audiobooks",
                "tts_models/en/vctk/vits": "🎭 VCTK - Multi-Speaker Natural",
                "tts_models/en/ljspeech/glow-tts": "⚡ GlowTTS - Fast & Clear"
            }
            default_voice = "tts_models/en/ljspeech/tacotron2-DDC"
        else:
            voice_options = {
                "en-US-AriaNeural": "🇺🇸 Aria - Most Natural",
                "en-US-JennyNeural": "🇺🇸 Jenny - Professional",
                "en-US-GuyNeural": "🇺🇸 Guy - Deep Voice",
                "en-GB-SoniaNeural": "🇬🇧 Sonia - British Accent",
                "en-AU-NatashaNeural": "🇦🇺 Natasha - Australian"
            }
            default_voice = "en-US-AriaNeural"
        
        selected_voice = st.selectbox(
            "Select Voice:",
            list(voice_options.keys()),
            format_func=lambda x: voice_options[x],
            index=0
        )
        
        # Quality indicators
        if selected_engine == "coqui-xtts":
            st.markdown('<span class="quality-badge">🏆 STUDIO QUALITY</span>', unsafe_allow_html=True)
            st.info("💡 Coqui TTS provides the most human-like voice synthesis")
        elif selected_engine == "edge-tts":
            st.markdown('<span class="quality-badge">✨ HIGH QUALITY</span>', unsafe_allow_html=True)
        
        # Performance Settings
        st.subheader("🚀 Performance")
        
        enable_caching = st.checkbox(
            "Enable Smart Caching",
            value=True,
            help="Cache audio segments to speed up processing"
        )
        
        if enable_caching:
            st.success("✅ Caching enabled - Faster processing!")
        
        # Voice sample
        if st.button("🎵 Test Voice Sample"):
            with st.spinner("Generating voice sample..."):
                try:
                    tts = TTSConverter(engine=selected_engine, voice=selected_voice)
                    tts.cache_enabled = enable_caching
                    sample_text = "Hello! This is how your audiobook will sound. The voice quality is crisp and natural."
                    
                    # Generate sample in temp file
                    temp_sample = os.path.join(settings.temp_dir, "voice_sample.mp3")
                    success = asyncio.run(tts.convert_text_to_audio(sample_text, temp_sample))
                    
                    if success and os.path.exists(temp_sample):
                        with open(temp_sample, 'rb') as audio_file:
                            st.audio(audio_file.read(), format='audio/mp3')
                        st.success("🎉 Voice sample generated!")
                    else:
                        st.error("Failed to generate voice sample")
                except Exception as e:
                    st.error(f"Error: {e}")
        
        # Cache information
        st.subheader("📊 Cache Status")
        try:
            tts = TTSConverter(engine=selected_engine, voice=selected_voice)
            cache_info = tts.get_cache_info()
            
            if cache_info.get("cache_enabled"):
                st.markdown(f"""
                <div class="cache-info">
                <strong>Cache Status:</strong> Active<br>
                <strong>Cached Items:</strong> {cache_info.get('cache_size', 0)}<br>
                <strong>Storage:</strong> {cache_info.get('cache_directory', 'N/A')}
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🗑️ Clear Cache"):
                    tts.clear_cache()
                    st.success("Cache cleared!")
                    st.experimental_rerun()
            else:
                st.info("Cache disabled")
        except:
            pass
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📚 Upload Your Book")
        
        uploaded_file = st.file_uploader(
            "Choose your book file",
            type=['epub', 'pdf', 'txt', 'mobi'],
            help="Supported formats: EPUB, PDF, TXT, MOBI"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            # Processing options
            st.subheader("📖 Processing Options")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                use_ai_processing = st.checkbox(
                    "🤖 AI Text Enhancement", 
                    value=True,
                    help="Use Gemini AI to optimize text for speech"
                )
                
                max_chapters = st.number_input(
                    "Max Chapters to Process",
                    min_value=1,
                    max_value=100,
                    value=30,
                    help="Limit processing for testing"
                )
            
            with col_b:
                speech_rate = st.slider(
                    "🎛️ Speech Rate",
                    min_value=0.5,
                    max_value=2.0,
                    value=1.0,
                    step=0.1,
                    help="Adjust speaking speed"
                )
                
                add_pauses = st.checkbox(
                    "⏸️ Enhanced Pauses",
                    value=True,
                    help="Add natural pauses between sections"
                )
            
            # Convert button
            if st.button("🚀 Convert to Audiobook", type="primary"):
                convert_book(
                    uploaded_file, 
                    selected_engine, 
                    selected_voice,
                    use_ai_processing,
                    max_chapters,
                    speech_rate,
                    add_pauses,
                    enable_caching
                )
    
    with col2:
        st.header("🎯 Features")
        
        features = [
            "🎙️ **Coqui TTS**: Studio-quality voice synthesis",
            "⚡ **Smart Caching**: 3x faster processing",
            "🤖 **AI Enhancement**: Gemini-powered text optimization", 
            "🎭 **Multiple Voices**: Choose your perfect narrator",
            "📱 **Easy Interface**: Drag, drop, and convert",
            "🔧 **Customizable**: Adjust speed, pauses, and quality",
            "💾 **Chapter Support**: Organized audio files",
            "🌟 **English Optimized**: Best quality for English books"
        ]
        
        for feature in features:
            st.markdown(feature)
        
        st.header("📈 Quality Comparison")
        
        quality_data = {
            "Engine": ["Coqui TTS", "Edge TTS", "Google TTS", "pyttsx3"],
            "Quality": ["🏆 Excellent", "✨ Very Good", "👍 Good", "📢 Basic"],
            "Speed": ["🐌 Slower", "⚡ Fast", "⚡ Fast", "🏃 Very Fast"],
            "Natural": ["💯 Perfect", "😊 High", "🙂 Medium", "🤖 Robotic"]
        }
        
        st.table(quality_data)
        
        st.info("💡 **Tip**: Use Coqui TTS for the most natural audiobook experience!")

def convert_book(uploaded_file, engine, voice, use_ai, max_chapters, speech_rate, add_pauses, enable_cache):
    """Convert uploaded book to audiobook."""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_path = tmp_file.name
        
        # Initialize components
        status_text.text("🔧 Initializing components...")
        progress_bar.progress(10)
        
        text_extractor = TextExtractor()
        text_processor = TextProcessor() if use_ai else None
        tts_converter = TTSConverter(engine=engine, voice=voice)
        tts_converter.cache_enabled = enable_cache
        audio_merger = AudioMerger()
        
        # Extract text
        status_text.text("📖 Extracting text from book...")
        progress_bar.progress(20)
           
        extracted_text = asyncio.run(text_extractor.extract_text(temp_path))
        
        if not extracted_text.get('chapters'):
            st.error("No text could be extracted from the file")
            return
        
        chapters = extracted_text['chapters'][:max_chapters]
        st.success(f"✅ Extracted {len(chapters)} chapters")
        
        # Process with AI if enabled
        if use_ai and text_processor:
            status_text.text("🤖 AI processing chapters...")
            progress_bar.progress(40)
            
            processed_chapters = asyncio.run(text_processor.process_chapters(chapters))
            chapters = processed_chapters
            st.success("✅ AI processing complete")
        
        # Convert to audio
        status_text.text(f"🎙️ Converting to audio using {engine}...")
        progress_bar.progress(60)
        
        audio_dir = os.path.join(settings.temp_dir, f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(audio_dir, exist_ok=True)
        
        audio_files = asyncio.run(tts_converter.convert_chapters_to_audio(chapters, audio_dir))
        
        if not audio_files:
            st.error("Failed to convert any chapters to audio")
            return
        
        st.success(f"✅ Converted {len(audio_files)} chapters to audio")
        
        # Merge audio files
        status_text.text("🔗 Merging audio files...")
        progress_bar.progress(80)
        
        output_filename = f"{uploaded_file.name.rsplit('.', 1)[0]}_audiobook.mp3"
        output_path = os.path.join(settings.output_dir, output_filename)
        
        success = await_merge_audio(audio_files, output_path, extracted_text.get('metadata', {}))
        
        if success:
            progress_bar.progress(100)
            status_text.text("✅ Audiobook created successfully!")
            
            # Display results
            st.success("🎉 **Audiobook conversion complete!**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📚 Chapters", len(chapters))
            with col2:
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                st.metric("💾 File Size", f"{file_size:.1f} MB")
            with col3:
                # Estimate duration
                total_text = " ".join([ch.get('text', '') for ch in chapters])
                duration = tts_converter.estimate_audio_duration(total_text)
                st.metric("⏱️ Duration", f"{duration/60:.1f} min")
            
            # Download button
            with open(output_path, 'rb') as audio_file:
                st.download_button(
                    label="📥 Download Audiobook",
                    data=audio_file.read(),
                    file_name=output_filename,
                    mime="audio/mpeg",
                    type="primary"
                )
            
            # Play preview
            st.subheader("🎵 Preview")
            with open(output_path, 'rb') as audio_file:
                st.audio(audio_file.read(), format='audio/mp3')
            
            # Cache info
            if enable_cache:
                cache_info = tts_converter.get_cache_info()
                st.info(f"📊 Cache now contains {cache_info.get('cache_size', 0)} items")
        
        else:
            st.error("❌ Failed to merge audio files")
    
    except Exception as e:
        st.error(f"❌ Error during conversion: {str(e)}")
        logger.error(f"Conversion error: {e}", exc_info=True)
    
    finally:
        # Cleanup
        try:
            os.unlink(temp_path)
        except:
            pass

def await_merge_audio(audio_files, output_path, metadata):
    """Wrapper to run async audio merger."""
    try:
        audio_merger = AudioMerger()
        return asyncio.run(audio_merger.merge_audio_files(audio_files, output_path, metadata))
    except Exception as e:
        logger.error(f"Audio merge error: {e}")
        return False

if __name__ == "__main__":
    main() 