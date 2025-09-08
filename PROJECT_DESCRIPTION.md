# FikrFree Assistant Bot

## Overview
FikrFree Assistant is an intelligent healthcare and insurance chatbot built for FikrFree (fikrfree.com.pk). It provides users with comprehensive information about healthcare plans, insurance coverage, partner platforms, doctor consultations, and claims processing through an interactive web interface.

## Key Features

### 🤖 Intelligent Chat Assistant
- **Bilingual Support**: Handles both English and Roman Urdu (Urdu written in English alphabet)
- **Language Detection**: Automatically detects user language and responds accordingly
- **RAG-Powered**: Uses Retrieval-Augmented Generation to provide accurate answers from healthcare data
- **Real-time Streaming**: Provides streaming responses for better user experience

### 🏥 Healthcare Knowledge Base
- **Insurance Plans**: Information about various healthcare plans (Bronze, Silver, Gold, etc.)
- **Partner Platforms**: Coverage for OlaDoc, MedIQ, BIMA, EFU, Waada, WebDoc
- **Doctor Consultations**: Telemedicine and booking information
- **Claims Processing**: SOPs and eligibility requirements
- **Pricing & Coverage**: Detailed plan comparisons and benefits

### 🔒 Safety & Security
- **Content Security Policy**: Implemented CSP middleware for web security
- **Input Sanitization**: Uses bleach for cleaning user inputs
- **Content Filtering**: Built-in toxicity detection and prompt injection protection
- **CORS Configuration**: Secure cross-origin resource sharing

### 📊 Data Management
- **CSV Processing**: Converts multiple CSV files containing partner details into searchable indexes
- **Vector Storage**: Uses FAISS for efficient similarity search
- **Persistent Storage**: Maintains indexes for quick response times
- **Feedback Collection**: Stores user feedback for continuous improvement

## Technical Architecture

### Backend (FastAPI)
- **Python Framework**: FastAPI with async support
- **AI/ML Stack**: 
  - LlamaIndex for document indexing and retrieval
  - OpenAI GPT-4o-mini for language generation
  - HuggingFace embeddings (BAAI/bge-small-en-v1.5)
- **Data Processing**: Pandas for CSV manipulation
- **Security**: LLM Guard for content safety

### Frontend
- **Web Interface**: Responsive HTML/CSS/JavaScript chat interface
- **Real-time Communication**: Server-sent events for streaming responses
- **Mobile-Friendly**: Toggle between web and mobile views
- **Accessibility**: ARIA labels and semantic HTML

### Data Sources
The bot processes healthcare partner data from multiple CSV files:
- BIMA insurance plans
- EFU insurance coverage
- MedIQ medical services
- OlaDoc doctor consultations
- Waada health benefits
- WebDoc telemedicine

## Use Cases

### For Customers
- **Plan Comparison**: "What's the difference between Bronze and Silver plans?"
- **Claims Guidance**: "How do I file a claim with BIMA?"
- **Doctor Booking**: "How can I book a consultation through OlaDoc?"
- **Coverage Queries**: "What does my plan cover for hospitalization?"

### For Support Teams
- **Quick Reference**: Instant access to plan details and SOPs
- **Multilingual Support**: Handle both English and Urdu-speaking customers
- **Consistent Information**: Standardized responses based on official data

## Getting Started

### Prerequisites
- Python 3.8+
- OpenAI API key
- Required dependencies (see requirements.txt)

### Installation
1. Install dependencies: `pip install -r requirements.txt`
2. Set up environment variables (OpenAI API key)
3. Process data: `python xlsx_table_splitter.py` (if needed)
4. Run the application: `uvicorn main:app --reload`

### Data Setup
The system processes Excel files containing partner details:
```bash
python xlsx_table_splitter.py "Raw/Fikrfree - Partners Details Complete.xlsx" ./data
```

## Project Structure
```
fikrfree-bot/
├── app/
│   ├── api.py              # FastAPI routes
│   ├── bot.py              # Core chat logic
│   ├── index_generator.py  # Data indexing
│   └── index_listener.py   # File monitoring
├── data/                   # CSV files with partner details
├── static/                 # Frontend assets
├── templates/              # HTML templates
├── main.py                 # FastAPI application
└── requirements.txt        # Dependencies
```

## Target Audience
- **Healthcare consumers** seeking insurance information
- **Insurance agents** needing quick plan details
- **Customer support teams** handling inquiries
- **FikrFree platform users** exploring healthcare options

## Technology Stack
- **Backend**: Python, FastAPI, LlamaIndex, OpenAI
- **Frontend**: HTML, CSS, JavaScript, jQuery
- **AI/ML**: GPT-4o-mini, HuggingFace Embeddings, FAISS
- **Data**: CSV processing, Vector databases
- **Security**: Content filtering, Input sanitization, CSP

## Future Enhancements
- Voice input/output capabilities (mic button prepared but commented)
- Advanced analytics and usage tracking
- Integration with more healthcare partners
- Enhanced multilingual support
- Mobile app development

---

FikrFree Assistant represents a comprehensive solution for healthcare information access, combining modern AI capabilities with practical healthcare data to serve Pakistani healthcare consumers effectively.