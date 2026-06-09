# ⚡ GenEV — AI-Powered EV Ownership Intelligence Platform

GenEV is a full-stack AI platform that simulates real-world EV scenarios, 
analyses battery performance, and provides AI-powered insights for Indian EV owners.

## 🚀 Live Demo
[genev.streamlit.app](https://genev.streamlit.app)

## 🛠️ Tech Stack
- **Frontend:** Streamlit
- **LLM:** Groq LLaMA 3.3 70B
- **RAG:** ChromaDB + Sentence Transformers
- **Auth + DB:** Supabase (PostgreSQL + RLS)
- **PDF Export:** ReportLab
- **Deployment:** Streamlit Cloud

## ✨ Features
- EV scenario simulation from natural language
- 6 performance metrics with letter grades
- RAG-powered AI chat about EV ownership in India
- Scenario comparison (up to 4 runs)
- PDF report export (Premium)
- Personal simulation history
- Subscription system (Free + Premium ₹299/mo)

## 🏃 Run Locally
```bash
git clone https://github.com/YOUR_USERNAME/genev.git
cd genev
pip install -r requirements.txt
streamlit run frontend/app.py
```

## 🔐 Environment Variables
Create a `.env` file with:
