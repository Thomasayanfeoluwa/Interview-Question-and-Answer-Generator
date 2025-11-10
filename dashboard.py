import streamlit as st
import os
import re
import pandas as pd
import time
from datetime import datetime
import base64
from src.helper import llm_pipeline

# Page configuration
st.set_page_config(
    page_title="AI Document Analyzer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
def inject_custom_css():
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2e86ab;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    .info-box {
        background-color: #f0f8ff;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin-bottom: 1.5rem;
    }
    .success-box {
        background-color: #f0fff4;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #38a169;
        margin-bottom: 1.5rem;
    }
    .progress-bar {
        background-color: #e2e8f0;
        border-radius: 10px;
        height: 25px;
        margin: 1rem 0;
    }
    .progress-fill {
        background: linear-gradient(90deg, #1f77b4, #2e86ab);
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    .qa-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }
    .qa-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .question-number {
        background: #1f77b4;
        color: white;
        border-radius: 50%;
        width: 35px;
        height: 35px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin-right: 10px;
    }
    .question-text {
        font-weight: 600;
        color: #2d3748;
        margin-bottom: 0.5rem;
        font-size: 1.1rem;
    }
    .answer-text {
        color: #4a5568;
        line-height: 1.6;
        padding-left: 45px;
    }
    .download-btn {
        background: linear-gradient(135deg, #1f77b4, #2e86ab);
        color: white;
        padding: 12px 24px;
        border: none;
        border-radius: 8px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
        transition: transform 0.2s ease;
    }
    .download-btn:hover {
        transform: translateY(-2px);
        text-decoration: none;
        color: white;
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #1f77b4, #2e86ab);
    }
    </style>
    """, unsafe_allow_html=True)

def clean_text(text):
    """Remove markdown formatting and special characters from text"""
    if not isinstance(text, str):
        text = str(text)
    
    # Remove markdown formatting
    text = re.sub(r'[\*\_\`]', '', text)
    
    # Remove any remaining numbering at start
    text = re.sub(r'^\s*\d+[\*\.]\s*', '', text)
    
    # Remove quotes that wrap entire content
    text = re.sub(r'^\"(.*)\"$', r'\1', text)
    text = re.sub(r"^\'(.*)\'$", r'\1', text)
    
    # Clean up quotes and extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Ensure proper sentence casing
    if text and len(text) > 1:
        text = text[0].upper() + text[1:]
    
    return text

def get_csv_download_link(df, filename):
    """Generate a download link for CSV file"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="download-btn">📥 Download CSV File</a>'
    return href

def main():
    # Inject custom CSS
    inject_custom_css()
    
    # Main header
    st.markdown('<h1 class="main-header">📚 AI Document Analyzer</h1>', unsafe_allow_html=True)
    st.markdown("### Transform PDF documents into professional Q&A interviews")
    
    # Detect theme colors automatically
    bg_color = "#F0F2F6" if st.get_option("theme.base") == "light" else "#0E1117"
    text_color = "#000000" if st.get_option("theme.base") == "light" else "#FFFFFF"

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        st.markdown(f"""
            <div style="
                background-color: {bg_color};
                color: {text_color};
                padding: 10px;
                border-radius: 8px;
                font-size: 14px;
                line-height: 1.6;
            ">
                <strong>How it works:</strong><br>
                1. Upload a PDF document<br>
                2. AI analyzes the content<br>
                3. Generate professional Q&A<br>
                4. Download formatted CSV
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📋 Supported Documents")
        st.markdown("""
        - Research Papers
        - Technical Documentation  
        - Business Reports
        - Academic Publications
        - Policy Documents
        """)
        
        st.markdown("---")
        st.markdown("**Note:** Processing time depends on document length and complexity (typically 2-5 minutes).")
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="sub-header">📤 Upload Document</div>', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type="pdf",
            help="Upload your PDF document for analysis"
        )
        
        if uploaded_file is not None:
            # Display file info
            file_details = {
                "Filename": uploaded_file.name,
                "File size": f"{uploaded_file.size / 1024:.1f} KB",
                "Upload time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            st.json(file_details)
            
            # Process button
            if st.button("🚀 Generate Interview Questions", type="primary", use_container_width=True):
                process_document(uploaded_file)
    
    with col2:
        st.markdown('<div class="sub-header">ℹ️ Instructions</div>', unsafe_allow_html=True)

        # Instructions box
        st.markdown("""
        <div style="
            padding: 10px;
            border-left: 4px solid #2c7be5;  /* Streamlit blue accent */
            border-radius: 4px;
            line-height: 1.6;
        ">
            <strong>For best results:</strong><br><br>
            ✅ Use well-structured PDF documents<br>
            ✅ Ensure text is selectable (not scanned images)<br>
            ✅ Documents should be in English<br>
            ✅ Optimal length: 5-50 pages<br>
            ✅ Clear formatting and headings
        </div>
        """, unsafe_allow_html=True)

        # Output includes box
        st.markdown("""
        <div style="
            padding: 10px;
            border-left: 4px solid #17a2b8;  /* info accent */
            border-radius: 4px;
            line-height: 1.6;
            margin-top: 10px;
        ">
            <strong>Output includes:</strong><br>
            <ul style="margin: 5px 0 0 15px; padding: 0;">
                <li>Numbered questions & answers</li>
                <li>Professional formatting</li>
                <li>Clean, markdown-free text</li>
                <li>Ready-to-use CSV format</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)



def process_document(uploaded_file):
    """Process the uploaded PDF document"""
    
    # Create temporary file
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, uploaded_file.name)
    
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    try:
        # Initialize session state for progress tracking
        if 'progress' not in st.session_state:
            st.session_state.progress = 0
        if 'current_qa' not in st.session_state:
            st.session_state.current_qa = None
        if 'qa_list' not in st.session_state:
            st.session_state.qa_list = []
        if 'processing_complete' not in st.session_state:
            st.session_state.processing_complete = False
        
        # Progress section
        st.markdown("---")
        st.markdown('<div class="sub-header">📊 Processing Progress</div>', unsafe_allow_html=True)
        
        # Progress bars
        progress_col1, progress_col2 = st.columns([3, 1])
        
        with progress_col1:
            overall_progress = st.progress(0)
            status_text = st.empty()
        
        with progress_col2:
            eta_text = st.empty()
            count_text = st.empty()
        
        # Processing steps
        steps = [
            "Reading PDF document...",
            "Analyzing content structure...",
            "Generating questions...",
            "Creating answers...",
            "Finalizing output..."
        ]
        
        # Simulate initial processing steps
        for i, step in enumerate(steps):
            status_text.text(step)
            overall_progress.progress((i + 1) * 0.1)
            time.sleep(1)  # Simulate processing time
        
        # Get questions and answers
        status_text.text("Generating questions and answers...")
        
        # Call your LLM pipeline
        result = llm_pipeline(temp_path)
        
        if len(result) >= 2:
            answer_generation_chain = result[0]
            ques_list = result[1]
            retriever = result[2] if len(result) > 2 else None
            llm_answer_gen = result[3] if len(result) > 3 else None
            
            # Limit to 25 questions for performance
            if len(ques_list) > 25:
                ques_list = ques_list[:25]
                st.info(f"Document analyzed: Limited to first 25 questions for optimal performance.")
            
            total_questions = len(ques_list)
            qa_data = []
            
            # Process each question
            for i, question in enumerate(ques_list):
                # Update progress
                progress = (i + 1) / total_questions
                overall_progress.progress(0.5 + (progress * 0.5))
                
                # Update status
                status_text.text(f"Processing question {i+1}/{total_questions}...")
                count_text.text(f"{i+1}/{total_questions}")
                eta_text.text(f"ETA: {((total_questions - i) * 5):.0f}s")
                
                # Clean question
                clean_question = clean_text(question)
                
                # Get answer
                try:
                    response = answer_generation_chain.invoke({"input": clean_question})
                    
                    if isinstance(response, dict):
                        answer = response.get("answer") or response.get("output") or response.get("result") or str(response)
                    else:
                        answer = str(response)
                    
                    clean_answer = clean_text(answer.strip())
                    
                except Exception as e:
                    clean_answer = f"Unable to generate answer: {str(e)}"
                
                # Store Q&A
                qa_data.append({
                    "No.": i + 1,
                    "Question": clean_question,
                    "Answer": clean_answer
                })
                
                # Update current Q&A for display
                st.session_state.current_qa = {
                    "index": i + 1,
                    "question": clean_question,
                    "answer": clean_answer
                }
                
                # Add to session state list
                st.session_state.qa_list = qa_data
                
                # Small delay to show progress
                time.sleep(2)
            
            # Complete processing
            overall_progress.progress(1.0)
            status_text.text("Processing complete!")
            st.session_state.processing_complete = True
            
            # Display results
            display_results(qa_data, uploaded_file.name)
            
        else:
            st.error("Failed to process document. Please try again with a different file.")
    
    except Exception as e:
        st.error(f"An error occurred during processing: {str(e)}")
        st.info("Please try again with a different PDF file.")
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

def display_results(qa_data, original_filename):
    """Display the generated questions and answers"""
    
    st.markdown("---")
    st.markdown('<div class="sub-header">📝 Generated Interview Questions & Answers</div>', unsafe_allow_html=True)
    
    # Success message
    st.markdown(f"""
    <div style="
        padding: 10px;
        border-left: 4px solid #28a745;  /* green accent for success */
        border-radius: 4px;
        line-height: 1.6;
    ">
        <strong>✅ Successfully Generated {len(qa_data)} Questions!</strong><br>
        Your document has been analyzed and professional Q&A pairs have been created.
    </div>
    """, unsafe_allow_html=True)

    # Create DataFrame for display and download
    df = pd.DataFrame(qa_data)
    
    # Display Q&A in a nice format
    for qa in qa_data:
        with st.container():
            st.markdown(f"""
            <div class="qa-card">
                <div class="question-text">
                    <span class="question-number">{qa['No.']}</span>
                    {qa['Question']}
                </div>
                <div class="answer-text">
                    {qa['Answer']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Download section
    st.markdown("---")
    st.markdown('<div class="sub-header">💾 Download Results</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Clean filename for download
        clean_name = os.path.splitext(original_filename)[0]
        clean_name = re.sub(r'[^\w\s-]', '', clean_name)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip().title()
        download_filename = f"{clean_name} - Interview Q&A.csv"
        
        # Create download link
        download_link = get_csv_download_link(df, download_filename)
        st.markdown(download_link, unsafe_allow_html=True)
    
    with col2:
        st.metric("Total Questions", len(qa_data))
        st.metric("Processing Time", "Complete")
    
    # Preview of CSV data
    with st.expander("📋 Preview CSV Data"):
        st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()