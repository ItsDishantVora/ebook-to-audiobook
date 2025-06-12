"""Main Streamlit application for the Audiobook Converter."""

import streamlit as st
import asyncio
import os
import logging
import tempfile
from pathlib import Path
from typing import Dict, List
import time

# Core modules  
from core import TextExtractor, TextProcessor, TTSConverter, AudioMerger
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Audiobook Converter",
    page_icon="🎧",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1e3a8a;
        margin-bottom: 2rem;
    }
    .feature-box {
        background-color: #f0f9ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3b82f6;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #f0fdf4;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #22c55e;
        color: #166534;
    }
    .warning-box {
        background-color: #fffbeb;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #f59e0b;
        color: #92400e;
    }
    .error-box {
        background-color: #fef2f2;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ef4444;
        color: #dc2626;
    }
</style>
""", unsafe_allow_html=True)

class AudiobookConverterApp:
    """Main application class."""
    
    def __init__(self):
        self.text_extractor = TextExtractor()
        self.text_processor = TextProcessor()
        self.tts_converter = TTSConverter()
        self.audio_merger = AudioMerger()
        
    def render_header(self):
        """Render the application header."""
        st.markdown("""
        <div class="main-header">
            <h1>🎧 Audiobook Converter</h1>
            <p>Transform your ebooks into high-quality audiobooks using AI</p>
        </div>
        """, unsafe_allow_html=True)
        
    def render_sidebar(self):
        """Render the sidebar with configuration options."""
        st.sidebar.title("⚙️ Configuration")
        
        # TTS Engine Selection
        st.sidebar.subheader("🎤 Text-to-Speech")
        
        tts_engine = st.sidebar.selectbox(
            "TTS Engine",
            options=['edge-tts', 'gtts', 'pyttsx3'],
            index=0,
            help="Choose your preferred TTS engine"
        )
        
        # Voice Selection
        available_voices = TTSConverter.get_available_voices()
        if tts_engine in available_voices:
            voice_options = available_voices[tts_engine]
            default_voice = settings.default_voice if settings.default_voice in voice_options else voice_options[0]
            
            selected_voice = st.sidebar.selectbox(
                "Voice",
                options=voice_options,
                index=voice_options.index(default_voice) if default_voice in voice_options else 0,
                help="Select the voice for narration"
            )
        else:
            selected_voice = settings.default_voice
        
        # Speech Settings
        st.sidebar.subheader("🔊 Audio Settings")
        speech_rate = st.sidebar.slider(
            "Speech Rate",
            min_value=0.5,
            max_value=2.0,
            value=settings.speech_rate,
            step=0.1,
            help="Adjust the speech speed"
        )
        
        silence_duration = st.sidebar.slider(
            "Silence Between Chapters (seconds)",
            min_value=0.5,
            max_value=5.0,
            value=settings.silence_duration,
            step=0.5,
            help="Duration of silence between chapters"
        )
        
        # Gemini Settings
        st.sidebar.subheader("🤖 AI Processing")
        use_gemini = st.sidebar.checkbox(
            "Use Gemini for text optimization",
            value=True,
            help="Use Google Gemini AI to optimize text for better TTS"
        )
        
        if use_gemini:
            chunk_size = st.sidebar.number_input(
                "Processing Chunk Size",
                min_value=5000,
                max_value=50000,
                value=settings.max_chunk_size,
                step=5000,
                help="Size of text chunks for Gemini processing"
            )
        else:
            chunk_size = settings.max_chunk_size
        
        # Cost Estimation
        if use_gemini:
            st.sidebar.info("💰 Estimated cost will be shown during processing")
        
        return {
            'tts_engine': tts_engine,
            'voice': selected_voice,
            'speech_rate': speech_rate,
            'silence_duration': silence_duration,
            'use_gemini': use_gemini,
            'chunk_size': chunk_size
        }
    
    def render_main_content(self, config: Dict):
        """Render the main content area."""
        
        # File Upload
        st.subheader("📚 Upload Your Ebook")
        
        uploaded_file = st.file_uploader(
            "Choose an ebook file",
            type=['epub', 'pdf', 'txt'],
            help="Upload your ebook in EPUB, PDF, or TXT format"
        )
        
        if uploaded_file is not None:
            # Display file info
            file_details = {
                "Filename": uploaded_file.name,
                "File size": f"{uploaded_file.size / (1024*1024):.2f} MB",
                "File type": uploaded_file.type
            }
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**File Details:**")
                for key, value in file_details.items():
                    st.write(f"- {key}: {value}")
            
            with col2:
                if st.button("🔄 Convert to Audiobook", type="primary"):
                    asyncio.run(self.process_ebook(uploaded_file, config))
        
        # Features section
        self.render_features()
    
    def render_features(self):
        """Render the features section."""
        st.subheader("✨ Features")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="feature-box">
                <h4>🤖 AI-Powered Processing</h4>
                <p>Uses Google Gemini AI to optimize text for natural-sounding speech</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="feature-box">
                <h4>🎯 Multiple TTS Engines</h4>
                <p>Choose from Edge TTS, Google TTS, or system TTS for the best quality</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="feature-box">
                <h4>💰 Cost-Effective</h4>
                <p>Optimized for minimal API costs with smart chunking and caching</p>
            </div>
            """, unsafe_allow_html=True)
    
    async def process_ebook(self, uploaded_file, config: Dict):
        """Process the uploaded ebook into an audiobook."""
        
        progress_container = st.container()
        with progress_container:
            st.markdown("### 🔄 Processing Your Ebook")
            
            # Create progress bars
            overall_progress = st.progress(0)
            step_progress = st.progress(0)
            status_text = st.empty()
            
            try:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    temp_input_path = tmp_file.name
                
                # Step 1: Extract text
                status_text.text("📖 Extracting text from ebook...")
                overall_progress.progress(10)
                
                extracted_data = await self.text_extractor.extract_text(temp_input_path)
                
                if not extracted_data:
                    st.error("❌ Failed to extract text from the ebook")
                    return
                
                # Display extraction results
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📄 Pages/Chapters", len(extracted_data['chapters']))
                with col2:
                    st.metric("📝 Word Count", f"{extracted_data['word_count']:,}")
                with col3:
                    estimated_duration = extracted_data['word_count'] / 150  # 150 words per minute
                    st.metric("⏱️ Est. Duration", f"{estimated_duration:.0f} min")
                
                overall_progress.progress(25)
                
                # Step 2: Process text with Gemini (if enabled)
                if config['use_gemini']:
                    status_text.text("🤖 Optimizing text with Gemini AI...")
                    
                    # Estimate cost
                    estimated_cost = self.text_processor.estimate_processing_cost(extracted_data['text'])
                    
                    if estimated_cost > 5.0:  # Warning for high costs
                        st.warning(f"⚠️ Estimated Gemini cost: ${estimated_cost:.2f}. Consider reducing chunk size.")
                        if not st.button("Continue anyway"):
                            return
                    else:
                        st.info(f"💰 Estimated Gemini cost: ${estimated_cost:.3f}")
                    
                    processed_chapters = await self.text_processor.process_chapters(extracted_data['chapters'])
                    overall_progress.progress(50)
                else:
                    status_text.text("📝 Using basic text processing...")
                    processed_chapters = extracted_data['chapters']
                    overall_progress.progress(50)
                
                # Step 3: Convert to audio  
                status_text.text("🎤 Converting text to speech...")
                
                # Update TTS converter settings
                self.tts_converter.engine = config['tts_engine']
                self.tts_converter.voice = config['voice']
                
                # Create temporary directory for audio files
                temp_audio_dir = tempfile.mkdtemp()
                
                audio_files = await self.tts_converter.convert_chapters_to_audio(
                    processed_chapters, temp_audio_dir
                )
                
                if not audio_files:
                    st.error("❌ Failed to convert text to speech")
                    return
                
                overall_progress.progress(80)
                
                # Step 4: Merge audio files
                status_text.text("🔗 Merging audio files...")
                
                # Create output filename
                safe_title = extracted_data['metadata']['title'].replace(' ', '_')
                safe_title = ''.join(c for c in safe_title if c.isalnum() or c in '_-')
                output_filename = f"{safe_title}_audiobook.mp3"
                output_path = os.path.join(settings.output_dir, output_filename)
                
                # Update audio merger settings
                self.audio_merger.silence_duration = config['silence_duration'] * 1000
                
                success = await self.audio_merger.merge_audio_files(
                    audio_files, output_path, extracted_data['metadata']
                )
                
                if not success:
                    st.error("❌ Failed to merge audio files")
                    return
                
                overall_progress.progress(100)
                status_text.text("✅ Audiobook created successfully!")
                
                # Display success message and download button
                st.markdown("""
                <div class="success-box">
                    <h4>🎉 Audiobook Created Successfully!</h4>
                    <p>Your audiobook has been generated and is ready for download.</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Audio info
                audio_info = self.audio_merger.get_audio_info(output_path)
                if audio_info:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🎵 Duration", f"{audio_info['duration_minutes']:.1f} min")
                    with col2:
                        st.metric("📊 File Size", f"{audio_info['file_size_mb']:.1f} MB")
                    with col3:
                        st.metric("🔊 Quality", f"{audio_info['sample_rate']} Hz")
                
                # Download button
                if os.path.exists(output_path):
                    with open(output_path, 'rb') as audio_file:
                        st.download_button(
                            label="📥 Download Audiobook",
                            data=audio_file.read(),
                            file_name=output_filename,
                            mime="audio/mpeg",
                            type="primary"
                        )
                
                # Cleanup
                os.unlink(temp_input_path)
                self.audio_merger.cleanup_temp_files(audio_files)
                
            except Exception as e:
                logger.error(f"Processing failed: {e}")
                st.markdown(f"""
                <div class="error-box">
                    <h4>❌ Processing Failed</h4>
                    <p>Error: {str(e)}</p>
                    <p>Please check your file and try again.</p>
                </div>
                """, unsafe_allow_html=True)
    
    def run(self):
        """Run the Streamlit application."""
        self.render_header()
        config = self.render_sidebar()
        self.render_main_content(config)

def main():
    """Main application entry point."""
    try:
        app = AudiobookConverterApp()
        app.run()
    except Exception as e:
        st.error(f"Application initialization failed: {e}")
        st.info("Please check your configuration and try again.")

if __name__ == "__main__":
    main() 