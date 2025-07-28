import speech_recognition as sr
from googletrans import Translator
from gtts import gTTS
import playsound
from pydub import AudioSegment
import os
import ipywidgets as widgets
from IPython.display import display

def translate_audio_file(audio_file_path, dest_language="en", source_language=None): 
    """
    Transcribes an audio file, translates the text to the specified language,
    and saves the translated audio. Handles different audio formats.
    """
    recognizer = sr.Recognizer()

    try:
        # Load the audio file using pydub (handles various formats)
        audio = AudioSegment.from_file(audio_file_path)

        # Convert to WAV if it's not already (SpeechRecognition likes WAV)
        if audio.frame_rate != 16000 or audio.channels != 1:
            audio = audio.set_frame_rate(16000).set_channels(1) # Standard sample rate and mono
        audio.export("temp_audio.wav", format="wav")  # Export to a temporary WAV file
        wav_file_path = "temp_audio.wav"

        with sr.AudioFile(wav_file_path) as source:
            recognizer.adjust_for_ambient_noise(source) # Adjust for noise
            audio_data = recognizer.record(source) # Read the entire audio file

        try:
            language_code = source_language if source_language else 'auto' # Use specified language or auto
            text = recognizer.recognize_google(audio_data, language=language_code)  # Auto-detect language
            print(f"Original text: {text}")
        except sr.UnknownValueError:
            print("Could not understand audio")
            return
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return

        translator = Translator()
        try:
            # Detect the source language (if not provided)
            detected_language = source_language if source_language else translator.detect(text).lang
            print(f"Detected source language: {detected_language}")  

            # Validate the detected language (add this check)
            if detected_language not in language_options.values() and source_language is None:  
                print(f"Warning: Unsupported source language: {detected_language}.  Defaulting to English.")
                detected_language = 'en'  

            translation = translator.translate(text, src=detected_language, dest=dest_language)
            print(f"Translated text ({dest_language}): {translation.text}")
        except Exception as e:
            print(f"Translation error: {e}")
            return

        try:
            converted_audio = gTTS(text=translation.text, lang=dest_language)
            converted_audio.save("translated_audio.mp3")
            print("Translated audio saved as translated_audio.mp3")
        except Exception as e:
            print(f"Text-to-speech or saving error: {e}")
            return
        finally:
            # Clean up the temporary WAV file
            if os.path.exists("temp_audio.wav"):
                os.remove("temp_audio.wav")

    except Exception as e:
        print(f"Error processing audio file: {e}")

def on_upload_clicked(b):
    """Handles the file upload event."""
    global uploaded_file_path

    for filename, uploaded_file in uploader.value.items():
        # Save the uploaded file to disk (you might want to handle file names better)
        uploaded_file_path = filename
        with open(filename, 'wb') as f:
            f.write(uploaded_file['content'])
        print(f"File uploaded: {filename}")
        break  # Only process the first file

    if uploaded_file_path:
        language = language_dropdown.value
        source_lang = source_language_dropdown.value 
        print(f"Translating to: {language} from {source_lang}")
        translate_audio_file(uploaded_file_path, dest_language=language, source_language=source_lang)
    else:
        print("No file uploaded.")

# Create a file upload button
uploader = widgets.FileUpload(
    accept='.mp3, .wav, .ogg',  
    multiple=False  
)

# Create a language selection dropdown
language_options = {
    'English': 'en',
    'Hindi': 'hi',
    'Marathi': 'mr',
    'Tamil': 'ta',
    'Telugu': 'te',
    'French': 'fr',
    'Spanish': 'es',
    'German': 'de',
    'Italian': 'it'
}

# Add source language dropdown
source_language_options = {
    'Auto Detect': None, 
    'English': 'en', 
    'Hindi': 'hi',
    'Marathi': 'mr',
    'Tamil': 'ta',
    'Telugu': 'te',
    'French': 'fr',
    'Spanish': 'es',
    'German': 'de',
    'Italian': 'it'
}

language_dropdown = widgets.Dropdown(
    options=language_options,
    value='en',  
    description='Translate to:'
)

source_language_dropdown = widgets.Dropdown( 
    options = source_language_options,
    value = None, 
    description = "Source Lang:"
)

# Create a button to trigger the translation
upload_button = widgets.Button(description="Upload and Translate")
upload_button.on_click(on_upload_clicked)

# Display the widgets
display(uploader)
display(language_dropdown)
display(source_language_dropdown)
display(upload_button)

uploaded_file_path = None
