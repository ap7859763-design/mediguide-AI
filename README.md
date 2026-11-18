# MediGuide – AI Health Information Assistant

A beginner-friendly BCA 5th semester Flask project. It provides general health education, has a responsive chat interface, includes basic safety routing for urgent symptoms, and can optionally connect to a local Ollama model.

## 1. Requirements
- Python 3.10 or newer
- VS Code (recommended)
- Internet is not required for the basic FAQ version
- Optional: Ollama + `llama3.2:1b` for local AI responses

## 2. Setup
Open this folder in VS Code. In the terminal run:

```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
```

Install packages:
```bash
pip install -r requirements.txt
```

Start the app:
```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## 3. Optional AI mode with Ollama
Install Ollama, then run:
```bash
ollama pull llama3.2:1b
ollama serve
```
Keep Ollama running and start the Flask app in another terminal. If Ollama is unavailable, MediGuide still works with built-in FAQ responses and safe fallback messages.

## 4. Main modules
- `app.py`: Flask backend, FAQ responses, emergency escalation, optional AI connection
- `templates/index.html`: chatbot layout
- `static/style.css`: responsive design
- `static/script.js`: chat interaction using Fetch API

## 5. Safety and limitations
This is an academic prototype, not a medical device. It does not diagnose, prescribe, or replace a healthcare professional. Do not enter personal identifiers or private medical records. Emergency symptoms require immediate professional help; in India call 112. The emergency keyword check is limited and may miss emergencies. Do not rely on this prototype for real medical decisions.

## 6. Suggested future enhancements
- Add multilingual Hindi/English toggle
- Add trusted public health FAQ content with citations
- Add login only if required, with privacy and security review
- Add doctor/hospital directory using verified local sources
- Add test cases for safety and chatbot responses
