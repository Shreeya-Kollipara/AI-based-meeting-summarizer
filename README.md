# AI-based-meeting-summarizer
🌟 AI Meeting Summarizer - Project Overview
The AI Meeting Summarizer is a web-based application that records, transcribes, summarizes, and translates meetings automatically. It helps users extract key points, decisions, and action items, and enables seamless task export to platforms like Trello, Asana, Jira, GitHub, and Notion.

🚀 Key Features
✅ Real-Time Audio Recording & Transcription using Vosk Speech Recognition
✅ Upload Audio Files for transcription & summarization
✅ Live Transcription Streaming for ongoing meetings
✅ Automatic Meeting Summaries with key points, decisions, and action items
✅ Task Export to Task Managers (Trello, Asana, GitHub, Jira, Notion)
✅ Multiple Export Formats (Markdown, JSON, CSV, HTML, Text)
✅ Language Translation Support – Meetings can be translated into multiple languages

🛠 Technology Stack
💻 Backend: Flask (Python)
🗣 Speech-to-Text: Vosk ASR (Automatic Speech Recognition)
🧠 Text Processing: NLP with SpaCy & Transformers (T5 Model)
🎵 Audio Handling: PyDub & FFmpeg
📌 Task Management Integration: API calls to Trello, Jira, Asana, GitHub, and Notion
🌎 Translation: Language translation support using NLP models
🎨 Frontend: HTML, CSS, JavaScript

📌 How It Works
1️⃣ Record or Upload a Meeting
Users can either record a live meeting or upload an audio file for processing.

2️⃣ Speech-to-Text Transcription
The system converts speech to text using the Vosk ASR model for high-accuracy transcription.

3️⃣ Automatic Meeting Summarization
The transcript is analyzed using NLP (SpaCy & Transformers) to extract:
✅ Key points
✅ Decisions made
✅ Action items
✅ Participants mentioned

4️⃣ Translate the Transcript
The extracted transcript can be translated into multiple languages using the translation module.

5️⃣ Task Export to Trello, Asana, Jira, GitHub, or Notion
Action items from the meeting can be exported directly to a task manager for seamless workflow integration.

6️⃣ Download Summary in Various Formats
The summarized meeting can be exported as Markdown, JSON, HTML, CSV, or plain text.

🌍 Audio Translation Tool
This repository includes a powerful audio translation tool that can transcribe audio files in any language and translate them into a desired target language. It leverages advanced speech recognition and machine translation technologies to provide high-quality translations.

✨ Key Features
🌎 Multi-Language Support – Transcribe & translate audio from any language into your preferred language.
🗣 Speech Recognition – Uses Google Speech Recognition to transcribe audio files.
🔄 Machine Translation – Employs Google Translate for accurate text translations.
🎙 Text-to-Speech Conversion – Converts translated text back into audio using Google Text-to-Speech (gTTS).
📂 User-Friendly Interface – Includes interactive widgets for easy file upload and language selection.

📌 How It Works
1️⃣ Audio Input: Upload an audio file using the file upload widget.
2️⃣ Transcription: The audio is transcribed into text using Google Speech Recognition.
3️⃣ Translation: The transcribed text is translated into the selected target language.
4️⃣ Text-to-Speech: The translated text is converted back into audio for playback.

📌 Use Cases
✅ 🌍 Global Communication – Enhance international business meetings, conferences, and collaborations.
✅ 📖 Language Learning – Assist language learners with real-time translations of audio materials.
✅ ♿ Accessibility – Improve accessibility for individuals with language barriers.


![image](https://github.com/user-attachments/assets/c646bfa3-b03b-44fc-93f8-7e6ccf7b0fa8)


