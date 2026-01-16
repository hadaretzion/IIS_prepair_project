# PrepAIr: CV Matching & Improvement Module

A Streamlit-based prototype for CV matching against job descriptions and providing AI-powered improvement suggestions. Built for Replit deployment.

## 🎯 Overview

This module helps job seekers:
- **Analyze CV-JD Match**: Get a score (0-100) and detailed breakdown of how well your CV matches a job description
- **Receive Improvement Suggestions**: Get actionable, grounded suggestions to improve your CV
- **Interactive Improvement**: Accept or ignore suggestions, see before/after comparisons
- **Export Final CV**: Download your improved CV as an editable DOCX file

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API Key (get from [Google AI Studio](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone or download this project**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up API Key:**
   
   In Replit:
   - Go to Secrets (lock icon in left sidebar)
   - Add a new secret: `GEMINI_API_KEY` = `your_api_key_here`
   
   Or set environment variable:
   ```bash
   # Linux/Mac
   export GEMINI_API_KEY="your_api_key_here"
   
   # Windows PowerShell
   $env:GEMINI_API_KEY="your_api_key_here"
   ```

4. **Run the app:**
   ```bash
   streamlit run app.py
   ```

   The app will open in your browser at `http://localhost:8501`

## 📖 Usage Guide

### Step 1: Upload Your CV
- Click "Choose a PDF file" to upload your CV
- The PDF must be text-based (not scanned)
- Minimum 500 characters required

### Step 2: Paste Job Description
- Paste the full job description in the text area
- Include requirements, responsibilities, and qualifications

### Step 3: Analyze
- Click "🔍 Analyze" button
- Wait for the analysis to complete
- View your match score and detailed breakdown

### Step 4: Improve CV
- Click "✨ Improve CV" to generate suggestions
- Review each suggestion in the right panel
- Click "✅ Accept" to apply a suggestion
- Click "❌ Ignore" to dismiss a suggestion
- For optional suggestions, check the confirmation box before accepting

### Step 5: Save & Download
- Click "💾 Save Version" to freeze your improved CV
- Click "📥 Download DOCX" to export as an editable Word document

## 📁 Project Structure

```
.
├── app.py                      # Main Streamlit application
├── services/                   # Core business logic modules
│   ├── pdf_extract.py         # PDF text extraction
│   ├── gemini_client.py       # Gemini API client
│   ├── cv_structurer.py       # CV structure extraction
│   ├── jd_structurer.py       # Job description structure extraction
│   ├── scoring.py             # Match score calculation
│   ├── suggestions.py         # Improvement suggestions engine
│   └── docx_export.py         # DOCX file generation
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🔧 Technical Details

### CV Matching Algorithm

The match score (0-100) is calculated using:
- **55%** - Required skills coverage
- **15%** - Preferred skills coverage
- **20%** - Responsibilities alignment (keyword matching)
- **10%** - Seniority level alignment

**Score Labels:**
- **85-100**: Excellent fit
- **70-84**: Mostly fit
- **50-69**: Partial fit
- **<50**: Weak fit

### Suggestions System

- Generates 6-10 actionable suggestions
- **Grounded**: Never invents experience, skills, or achievements
- **Anchored**: Each suggestion references a specific part of your CV
- **Risk-aware**: Categorizes suggestions as low/medium/high risk
- **Confirmation**: Optional suggestions require user confirmation before applying

### Supported Suggestion Types

- **rewrite**: Improve wording/emphasis of existing content
- **reorder**: Move content to better position
- **delete**: Remove redundant/irrelevant content
- **clarify**: Make vague statements more specific
- **add_optional**: Add content if user has it (requires confirmation)

## ⚠️ Limitations & Notes

- **Prototype Quality**: This is a study/project prototype, not production-ready
- **PDF Format**: Only text-based PDFs are supported (scanned PDFs won't work)
- **Token Limits**: Large CVs/JDs may be truncated
- **No Database**: All state is stored in Streamlit session_state (resets on page refresh)
- **English Only**: Optimized for English-language tech/programming job descriptions

## 🛠️ Troubleshooting

### "GEMINI_API_KEY not set"
- Ensure you've set the API key in Replit Secrets or as an environment variable
- Restart the Streamlit app after setting the key

### "PDF extraction failed"
- Your PDF may be scanned or image-based
- Try using a text-based PDF (created in Word, Google Docs, etc.)
- Minimum 500 characters required

### "Analysis failed" or JSON parsing errors
- Check your internet connection
- Verify your Gemini API key is valid
- Try again - the API may be temporarily unavailable

### Suggestions not appearing
- Ensure you've run "Analyze" first
- Check that both CV and JD are provided
- Some CVs may have fewer improvement opportunities

## 📝 License

This is a study project prototype. Use at your own discretion.

## 🤝 Contributing

This is a prototype project. Feel free to fork and adapt for your needs.

---

**Built with ❤️ using Streamlit and Google Gemini 2.5 Pro**
