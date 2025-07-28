import os
import json
import wave
import re
import datetime
import pyaudio
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment
from transformers import pipeline
import spacy
import pandas as pd


# Constants
FRAME_RATE = 16000
CHANNELS = 1
MODEL_PATH = "vosk-model-en-us-0.22"
OUTPUT_FORMATS = ["text", "json", "markdown", "html", "csv"]

# Task management integration options
TASK_INTEGRATIONS = {
    "jira": {"api_key": None, "url": "https://your-instance.atlassian.net"},
    "trello": {"api_key": None, "token": ""},
    "asana": {"api_key": None},
    "notion": {"token": None},
    "github": {"token": None}
}

from trello import TrelloClient
from trello.exceptions import ResourceUnavailable
import datetime

# Replace these with your actual Trello API credentials
TRELLO_API_KEY = "05fee9ca91c6b4c5bee27c5bfb39dba5"
TRELLO_TOKEN = "ATTA76b97f6eda7be25394115f56bcf21b73048abb5bc724678399416569c4b81f7eDEA08A16"

client = TrelloClient(
    api_key=TRELLO_API_KEY,
    token=TRELLO_TOKEN
)

def create_trello_tasks(board_name, tasks):
    try:
        boards = client.list_boards()
        
        # Find or create the board
        board = next((b for b in boards if b.name == board_name), None)
        if not board:
            board = client.add_board(board_name)

        # Create a list for today’s tasks
        today_list = board.add_list(f"Tasks for {datetime.datetime.now().strftime('%Y-%m-%d')}")

        results = []
        for task in tasks:
            card = today_list.add_card(task["task"])
            results.append({"task": task["task"], "status": "Added to Trello"})

        return {"status": "success", "results": results}

    except ResourceUnavailable:
        return {"status": "error", "message": "Trello board not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class MeetingSummarizer:
    def __init__(self, config=None):
        """Initialize the meeting summarizer with optional configuration."""
        self.config = config or {}
        self.transcript = ""
        self.summary = ""
        self.key_points = []
        self.decisions = []
        self.action_items = []
        self.participants = set()
        
        # Initialize models
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Vosk model not found! Download it from https://alphacephei.com/vosk/models and extract to {MODEL_PATH}")
        
        self.speech_model = Model(MODEL_PATH)
        self.recognizer = KaldiRecognizer(self.speech_model, FRAME_RATE)
        self.recognizer.SetWords(True)
        
        # Load NLP Models
        self.summarizer = pipeline("summarization", model="t5-small")
        self.nlp = spacy.load("en_core_web_sm")
        
    def convert_audio(self, input_path):
        """Converts any audio file (MP3, OGG, WAV) into WAV format for Vosk."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Audio file '{input_path}' not found!")

        output_path = "converted_audio.wav"

        try:
            audio = AudioSegment.from_file(input_path)
            audio = audio.set_channels(CHANNELS).set_frame_rate(FRAME_RATE)
            audio.export(output_path, format="wav")
            return output_path
        except Exception as e:
            raise RuntimeError(f"Failed to convert audio: {e}")

    
    def transcribe_audio(self, audio_path):
        """Transcribes the given WAV file using Vosk with timestamps."""
        wf = wave.open(audio_path, "rb")
        
        if wf.getnchannels() != CHANNELS or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            print("Audio file must be WAV format mono PCM.")
            return ""
        
        # Process audio in chunks
        results = []
        last_text = ""
        
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                if 'text' in result and result['text'] != last_text:
                    results.append(result)
                    last_text = result['text']
        
        # Get final result
        final_result = json.loads(self.recognizer.FinalResult())
        if 'text' in final_result:
            results.append(final_result)
        
        # Format transcript with timestamps
        transcript = ""
        for i, res in enumerate(results):
            if res.get('text', '').strip():
                # Convert from seconds to MM:SS format
                if 'result' in res and len(res['result']) > 0:
                    start_time = res['result'][0].get('start', 0)
                    minutes, seconds = divmod(int(start_time), 60)
                    timestamp = f"[{minutes:02d}:{seconds:02d}] "
                else:
                    timestamp = ""
                
                transcript += f"{timestamp}{res.get('text', '')}\n"
        
        self.transcript = transcript
        return transcript
    
    def record_audio(self, seconds=600, output_filename="recorded_audio.wav"):
        """Records audio from the microphone and saves it as WAV."""
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=CHANNELS, rate=FRAME_RATE, input=True, frames_per_buffer=1024)

        print("Recording... Press Ctrl+C to stop recording.")
        frames = []
        
        try:
            for _ in range(int(FRAME_RATE / 1024 * seconds)):
                frames.append(stream.read(1024))
                if _ % int(FRAME_RATE / 1024) == 0:  # Every second
                    print(f"Recording: {_ // int(FRAME_RATE / 1024)} seconds", end="\r")
        except KeyboardInterrupt:
            print("\nRecording stopped by user.")
        finally:
            print("\nProcessing audio...")
            stream.stop_stream()
            stream.close()
            p.terminate()

        with wave.open(output_filename, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(FRAME_RATE)
            wf.writeframes(b"".join(frames))

        return output_filename
    
    def live_transcription_generator(self, buffer_time=5):
        """Generator that yields real-time transcription segments with timestamps."""
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=CHANNELS, rate=FRAME_RATE, input=True, frames_per_buffer=1024)
        
        buffer = []
        buffer_frames = int(FRAME_RATE / 1024 * buffer_time)
        
        try:
            while True:
                data = stream.read(1024)
                buffer.append(data)
                
                if len(buffer) > buffer_frames:
                    # Process the oldest chunk in the buffer
                    oldest_chunk = buffer.pop(0)
                    if self.recognizer.AcceptWaveform(oldest_chunk):
                        result = json.loads(self.recognizer.Result())
                        if result.get('text', '').strip():
                            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                            transcript_segment = f"[{timestamp}] {result['text']}"
                            self.transcript += transcript_segment + "\n"
                            yield transcript_segment
        
        except Exception as e:
            # Process any remaining audio in the buffer
            for chunk in buffer:
                self.recognizer.AcceptWaveform(chunk)
            final_result = json.loads(self.recognizer.FinalResult())
            if final_result.get('text', '').strip():
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                transcript_segment = f"[{timestamp}] {final_result['text']}"
                self.transcript += transcript_segment + "\n"
                yield transcript_segment
            
            yield f"Transcription stopped: {str(e)}"
        
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
    
    def _extract_entities(self, text):
        """Extract named entities from the text."""
        doc = self.nlp(text)
        entities = {}
        
        for ent in doc.ents:
            if ent.label_ not in entities:
                entities[ent.label_] = []
            entities[ent.label_].append(ent.text)
            
            # Extract possible participants
            if ent.label_ == "PERSON":
                self.participants.add(ent.text)
                
        return entities
    
    

    def _extract_action_items(self, text):
        """Extract action items from the transcript."""
        
        # 🛑 Remove timestamps (e.g., [00:07])
        cleaned_text = re.sub(r"\[\d{2}:\d{2}\]", "", text).strip()

        # ✅ Updated action item patterns (more precise)
        action_patterns = [
            r"(?:TODO|To-Do|To Do)[:]? (.+)",  # Matches "TODO: Finish report"
            r"(?:assign|assigned to|task for)\s+(.*?)(?:\.|$)",  # Matches "Assigned to John"
            r"(.*?)(?: must| should| needs to| has to| will| shall) (.*?)(?:\.|$)",  # Matches "Sarah should prepare slides."
            r"(?:Action item|Follow up)[:]? (.+)",  # Matches "Action item: Schedule meeting"
        ]

        action_items = []
        
        for pattern in action_patterns:
            matches = re.finditer(pattern, cleaned_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                action = match.group(1).strip()

                # 🛑 Avoid very short or meaningless matches
                if action and len(action) > 5:
                    # ✅ Extract possible assignee
                    doc = self.nlp(action)
                    assignee = None
                    for ent in doc.ents:
                        if ent.label_ == "PERSON":
                            assignee = ent.text
                            break

                    action_items.append({
                        "task": action,
                        "assignee": assignee if assignee else "Not assigned",
                        "status": "Open",
                        "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })

        self.action_items = action_items
        return action_items

    
    
    import re

    def _extract_decisions(self, text):
        """Extract decisions made during the meeting."""
        decision_patterns = [
            r"\b(?:decided|concluded|agreed|determined)\s*(?:to|that|on)?\s*(.*?)(?:\.|$)",
            r"\b(?:the\s+decision|it\s+was\s+decided|we\s+agreed|the\s+team\s+concluded)\s*(?:to|that)?\s*(.*?)(?:\.|$)"
        ]

        decisions = []
        for pattern in decision_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                decision = match.group(1).strip()
                if decision and len(decision) > 5:  # Avoid short junk matches
                    decisions.append(decision)

        self.decisions = decisions
        return decisions

    
    def _summarize_text(self, text):
        """Summarize the transcript text."""
        if not text.strip():
            return "No significant text detected."
        
        # Split text into manageable chunks for the model
        tokens = text.split(" ")
        chunk_size = 500  # Smaller chunks for better processing
        chunks = [" ".join(tokens[i:i+chunk_size]) for i in range(0, len(tokens), chunk_size)]
        
        # Process each chunk
        summaries = []
        for chunk in chunks:
            if len(chunk.strip()) > 100:  # Only process substantial chunks
                summary = self.summarizer(chunk, max_length=150, min_length=30, do_sample=False)
                if summary and isinstance(summary, list) and "summary_text" in summary[0]:
                    summaries.append(summary[0]["summary_text"])
        
        # Combine summaries
        combined_summary = "\n\n".join(summaries)
        
        # Extract key points
        doc = self.nlp(combined_summary)
        key_points = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 10]

        self.key_points = key_points[:5]  # Limit to top 5 key points
        self.summary = combined_summary
        return combined_summary

    
    def process_transcript(self, transcript=None):
        """Process the transcript to extract insights."""
        if transcript:
            self.transcript = transcript
            
        # Ensure we have a transcript
        if not self.transcript:
            return {"error": "No transcript available to process"}
            
        # Generate summary
        summary = self._summarize_text(self.transcript)
        
        # Extract entities
        entities = self._extract_entities(self.transcript)
        
        # Extract action items
        action_items = self._extract_action_items(self.transcript)
        
        # Extract decisions
        decisions = self._extract_decisions(self.transcript)
        
        return {
            "summary": summary,
            "key_points": self.key_points,
            "entities": entities,
            "action_items": action_items,
            "decisions": decisions,
            "participants": list(self.participants),
            "full_transcript": self.transcript
        }
    
    def generate_output(self, format_type="markdown", output_file=None):
        """Generate formatted output based on user preference."""
        if format_type not in OUTPUT_FORMATS:
            return {"error": f"Unsupported format. Choose from: {', '.join(OUTPUT_FORMATS)}"}
        
        meeting_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        if format_type == "text":
            output = f"MEETING SUMMARY - {meeting_date}\n\n"
            output += "SUMMARY:\n" + self.summary + "\n\n"
            output += "KEY POINTS:\n" + "\n".join([f"- {point}" for point in self.key_points]) + "\n\n"
            output += "DECISIONS:\n" + "\n".join([f"- {decision}" for decision in self.decisions]) + "\n\n"
            output += "ACTION ITEMS:\n" + "\n".join([f"- {item['task']} " + (f"[Assigned to: {item['assignee']}]" if item['assignee'] else "") for item in self.action_items]) + "\n\n"
            output += "PARTICIPANTS:\n" + "\n".join([f"- {participant}" for participant in self.participants]) + "\n\n"
            output += "FULL TRANSCRIPT:\n" + self.transcript
            
        elif format_type == "markdown":
            output = f"# Meeting Summary - {meeting_date}\n\n"
            output += "## Summary\n" + self.summary + "\n\n"
            output += "## Key Points\n" + "\n".join([f"- {point}" for point in self.key_points]) + "\n\n"
            output += "## Decisions\n" + "\n".join([f"- {decision}" for decision in self.decisions]) + "\n\n"
            output += "## Action Items\n" + "\n".join([f"- {item['task']} " + (f"**[Assigned to: {item['assignee']}]**" if item['assignee'] else "") for item in self.action_items]) + "\n\n"
            output += "## Participants\n" + "\n".join([f"- {participant}" for participant in self.participants]) + "\n\n"
            output += "## Full Transcript\n```\n" + self.transcript + "\n```"
            
        elif format_type == "html":
            transcript_html = self.transcript.replace("\n", "<br>")
            output = f"""<!DOCTYPE html>
        <html>
        <head>
            <title>Meeting Summary - {meeting_date}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1, h2 {{ color: #333; }}
                .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
                .action-item {{ background-color: #fffde7; padding: 10px; margin-bottom: 5px; border-left: 3px solid #fbc02d; }}
                .assignee {{ font-weight: bold; color: #1976d2; }}
                .transcript {{ background-color: #f5f5f5; padding: 15px; max-height: 300px; overflow-y: auto; font-family: monospace; }}
            </style>
        </head>
        <body>
            <h1>Meeting Summary - {meeting_date}</h1>
            
            <h2>Summary</h2>
            <div class="summary">{self.summary}</div>
            
            <h2>Key Points</h2>
            <ul>
                {''.join(f'<li>{point}</li>' for point in self.key_points)}
            </ul>
            
            <h2>Decisions</h2>
            <ul>
                {''.join(f'<li>{decision}</li>' for decision in self.decisions)}
            </ul>
            
            <h2>Action Items</h2>
            <div>
                {''.join(f'<div class="action-item">{item["task"]} ' + (f'<span class="assignee">[Assigned to: {item["assignee"]}]</span>' if item["assignee"] else "") + '</div>' for item in self.action_items)}
            </div>
            
            <h2>Participants</h2>
            <ul>
                {''.join(f'<li>{participant}</li>' for participant in self.participants)}
            </ul>
            
            <h2>Full Transcript</h2>
            <div class="transcript">{transcript_html}</div>
        </body>
        </html>"""



            
        elif format_type == "json":
            output_dict = {
                "meeting_date": meeting_date,
                "summary": self.summary,
                "key_points": self.key_points,
                "decisions": self.decisions,
                "action_items": self.action_items,
                "participants": list(self.participants),
                "transcript": self.transcript
            }
            output = json.dumps(output_dict, indent=2)
            
        elif format_type == "csv":
            # Create DataFrames for each section
            summary_df = pd.DataFrame({"Summary": [self.summary]})
            key_points_df = pd.DataFrame({"Key Points": self.key_points})
            decisions_df = pd.DataFrame({"Decisions": self.decisions})
            action_items_df = pd.DataFrame(self.action_items)
            participants_df = pd.DataFrame({"Participants": list(self.participants)})
            
            # Write to multiple CSV files or one combined file
            if output_file:
                base_name = os.path.splitext(output_file)[0]
                summary_df.to_csv(f"{base_name}_summary.csv", index=False)
                key_points_df.to_csv(f"{base_name}_key_points.csv", index=False)
                decisions_df.to_csv(f"{base_name}_action_items.csv", index=False)
                participants_df.to_csv(f"{base_name}_participants.csv", index=False)
                output = f"CSV files written to {base_name}_*.csv"
            else:
                output = "CSV output requires a file name."
        
        # Write to file if specified
        if output_file and format_type != "csv":
            with open(output_file, "w", encoding="utf-8") as file:
                file.write(output)
                
        return output
    
    def generate_custom_output(self, format_options=None, output_file=None):
        """
        Generate a customized output format based on user preferences.
        
        Parameters:
        format_options (dict): Dictionary of format options with the following possible keys:
            - 'sections': List of sections to include ['summary', 'key_points', 'decisions', 'action_items', 'participants', 'transcript']
            - 'style': Formatting style ('minimal', 'detailed', 'business')
            - 'date_format': Format for date display (e.g., '%Y-%m-%d', '%B %d, %Y')
            - 'include_timestamps': Boolean to include timestamps in transcript
            - 'action_item_format': Format for action items ('simple', 'detailed', 'kanban')
            - 'highlight_terms': List of terms to highlight in the output
            - 'sort_action_items_by': Field to sort action items ('assignee', 'status', 'created')
            - 'max_transcript_length': Number of characters to include from transcript (0 for full transcript)
        output_file (str): Path to save the output file
        
        Returns:
        str: Formatted output based on user preferences
        """
        # Default format options if none provided
        if format_options is None:
            format_options = {
                'sections': ['summary', 'key_points', 'decisions', 'action_items', 'participants'],
                'style': 'detailed',
                'date_format': '%Y-%m-%d %H:%M',
                'include_timestamps': True,
                'action_item_format': 'detailed',
                'highlight_terms': [],
                'sort_action_items_by': None,
                'max_transcript_length': 0
            }
        
        # Get current date/time in requested format
        date_format = format_options.get('date_format', '%Y-%m-%d %H:%M')
        meeting_date = datetime.datetime.now().strftime(date_format)
        
        # Determine which sections to include
        sections = format_options.get('sections', ['summary', 'key_points', 'decisions', 'action_items', 'participants'])
        
        # Apply style template
        style = format_options.get('style', 'detailed')
        
        # Process highlight terms
        highlight_terms = format_options.get('highlight_terms', [])
        
        # Sort action items if requested
        sort_by = format_options.get('sort_action_items_by')
        action_items = self.action_items.copy()
        if sort_by and action_items:
            if isinstance(action_items[0], dict) and sort_by in action_items[0]:
                action_items = sorted(action_items, key=lambda x: x.get(sort_by, ''))
        
        # Format action items according to preference
        action_item_format = format_options.get('action_item_format', 'detailed')
        
        # Process transcript
        max_transcript_length = format_options.get('max_transcript_length', 0)
        transcript = self.transcript
        
        if max_transcript_length > 0 and len(transcript) > max_transcript_length:
            transcript = transcript[:max_transcript_length] + "... [truncated]"
        
        if not format_options.get('include_timestamps', True):
            # Remove timestamps (e.g., [00:07])
            transcript = re.sub(r"\[\d{2}:\d{2}\]", "", transcript).strip()
        
        # Generate output based on style
        if style == 'minimal':
            output = f"Meeting Summary - {meeting_date}\n\n"
            
            if 'summary' in sections:
                output += f"{self.summary}\n\n"
            
            if 'key_points' in sections:
                output += "Key Points:\n" + "\n".join([f"• {point}" for point in self.key_points]) + "\n\n"
            
            if 'action_items' in sections:
                output += "Action Items:\n" + "\n".join([f"• {item['task']}" for item in action_items]) + "\n\n"
        
        elif style == 'business':
            output = f"MEETING SUMMARY REPORT\nDate: {meeting_date}\n\n"
            
            if 'summary' in sections:
                output += "EXECUTIVE SUMMARY\n" + "="*20 + "\n" + self.summary + "\n\n"
            
            if 'key_points' in sections:
                output += "KEY DISCUSSION POINTS\n" + "="*20 + "\n"
                for i, point in enumerate(self.key_points, 1):
                    output += f"{i}. {point}\n"
                output += "\n"
            
            if 'decisions' in sections:
                output += "DECISIONS MADE\n" + "="*20 + "\n"
                for i, decision in enumerate(self.decisions, 1):
                    output += f"{i}. {decision}\n"
                output += "\n"
            
            if 'action_items' in sections:
                output += "ACTION ITEMS\n" + "="*20 + "\n"
                if action_item_format == 'detailed':
                    for i, item in enumerate(action_items, 1):
                        output += f"{i}. Task: {item['task']}\n"
                        output += f"   Assignee: {item['assignee']}\n"
                        output += f"   Status: {item['status']}\n"
                        output += f"   Created: {item['created']}\n\n"
                else:
                    for i, item in enumerate(action_items, 1):
                        output += f"{i}. {item['task']} (Assignee: {item['assignee']})\n"
                output += "\n"
            
            if 'participants' in sections:
                output += "MEETING PARTICIPANTS\n" + "="*20 + "\n"
                for participant in self.participants:
                    output += f"• {participant}\n"
                output += "\n"
            
            if 'transcript' in sections:
                output += "MEETING TRANSCRIPT\n" + "="*20 + "\n" + transcript + "\n"
        
        else:  # detailed is the default
            output = f"# Meeting Summary - {meeting_date}\n\n"
            
            if 'summary' in sections:
                output += "## Summary\n" + self.summary + "\n\n"
            
            if 'key_points' in sections:
                output += "## Key Points\n" + "\n".join([f"- {point}" for point in self.key_points]) + "\n\n"
            
            if 'decisions' in sections:
                output += "## Decisions\n" + "\n".join([f"- {decision}" for decision in self.decisions]) + "\n\n"
            
            if 'action_items' in sections:
                output += "## Action Items\n"
                if action_item_format == 'detailed':
                    for item in action_items:
                        output += f"- **Task:** {item['task']}\n"
                        output += f"  - Assignee: {item['assignee']}\n"
                        output += f"  - Status: {item['status']}\n"
                        output += f"  - Created: {item['created']}\n\n"
                elif action_item_format == 'kanban':
                    # Group by status
                    status_groups = {}
                    for item in action_items:
                        status = item['status']
                        if status not in status_groups:
                            status_groups[status] = []
                        status_groups[status].append(item)
                    
                    for status, items in status_groups.items():
                        output += f"### {status}\n"
                        for item in items:
                            output += f"- {item['task']} (Assignee: {item['assignee']})\n"
                        output += "\n"
                else:
                    for item in action_items:
                        assignee = f" [Assigned to: {item['assignee']}]" if item['assignee'] != "Not assigned" else ""
                        output += f"- {item['task']}{assignee}\n"
                output += "\n"
            
            if 'participants' in sections:
                output += "## Participants\n" + "\n".join([f"- {participant}" for participant in self.participants]) + "\n\n"
            
            if 'transcript' in sections:
                output += "## Full Transcript\n```\n" + transcript + "\n```"
        
        # Apply term highlighting
        if highlight_terms:
            for term in highlight_terms:
                if style == 'business':
                    replacement = f"**{term}**"
                else:
                    replacement = f"**{term}**"
                output = re.sub(r'\b' + re.escape(term) + r'\b', replacement, output, flags=re.IGNORECASE)
        
        # Write to file if specified
        if output_file:
            with open(output_file, "w", encoding="utf-8") as file:
                file.write(output)
        
        return output
    
    def export_to_task_system(self, system_name, credentials=None):
        """Export action items to a task management system."""
        if not self.action_items:
            return {"error": "No action items to export"}
            
        if system_name not in TASK_INTEGRATIONS:
            return {"error": f"Unsupported task system. Choose from: {', '.join(TASK_INTEGRATIONS.keys())}"}
            
        # Update credentials if provided
        if credentials:
            for key, value in credentials.items():
                TASK_INTEGRATIONS[system_name][key] = value
                
        # Check for required credentials
        for key, value in TASK_INTEGRATIONS[system_name].items():
            if value is None:
                return {"error": f"Missing required credential: {key} for {system_name}"}
                
        # Implement specific integrations
        if system_name == "jira":
            return self._export_to_jira()
        elif system_name == "trello":
            return self._export_to_trello()
        elif system_name == "asana":
            return self._export_to_asana()
        elif system_name == "github":
            return self._export_to_github()
        elif system_name == "notion":
            return self._export_to_notion()
            
        return {"error": "Integration not implemented yet"}
    
    
    
    def _export_to_trello(self):
        """Export action items to Trello."""
        # Placeholder for Trello API integration
        print("Exporting to Trello...")
        return {"status": "simulated", "message": "Would export action items to Trello if configured"}
    
    def _export_to_asana(self):
        """Export action items to Asana."""
        # Placeholder for Asana API integration
        print("Exporting to Asana...")
        return {"status": "simulated", "message": "Would export action items to Asana if configured"}
    
    def _export_to_github(self):
        """Export action items to GitHub Issues."""
        # Placeholder for GitHub API integration
        print("Exporting to GitHub Issues...")
        return {"status": "simulated", "message": "Would export action items to GitHub Issues if configured"}
    
    def _export_to_notion(self):
        """Export action items to Notion."""
        # Placeholder for Notion API integration
        print("Exporting to Notion...")
        return {"status": "simulated", "message": "Would export action items to Notion if configured"}

# For import in other modules
def create_summarizer(config=None):
    return MeetingSummarizer(config)