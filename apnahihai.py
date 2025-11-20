#!/usr/bin/env python3
import os
import threading
import requests
from flask import Flask, request, send_file, jsonify
from bs4 import BeautifulSoup
from pydub import AudioSegment

# --- TELEGRAM LIBRARY IMPORTS (UPDATED FOR v20+) ---
# We import 'Update' from 'telegram' and 'filters' from 'telegram.ext'
# We import 'Application', 'CommandHandler', etc., from 'telegram.ext'
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

# ==============================================================================
# --- CONFIGURATION (EDIT THIS SECTION) ---
# ==============================================================================

# 1. Paste your Telegram Bot Token here
TELEGRAM_BOT_TOKEN = "8211052420:AAFlpU5Xlp57ttx3sx03o52qbajPWEB-K8w"

# 2. Flask server configuration
# This runs locally on your machine. The bot will communicate with it.
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_SERVER_URL = f"http://{FLASK_HOST}:{FLASK_PORT}/download"

# ==============================================================================
# --- FLASK SERVER (The Processing Brain) ---
# ==============================================================================

app = Flask(__name__)

# Alternative scraping APIs for Instagram reels
SCRAPING_APIS = [
    "https://insta-api.snapsaveapp.com/download",
    "https://instagram-downloader-download-video.p.rapidapi.com/index",
]

def get_video_url(instagram_url):
    """Attempts to fetch the direct download link for an Instagram video using multiple services."""
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        
        # Try yt-dlp as a fallback (most reliable)
        try:
            import yt_dlp
            ydl_opts = {
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(instagram_url, download=False)
                if info and 'url' in info:
                    return info['url']
        except ImportError:
            print("yt-dlp not installed. Trying alternative methods...")
        except Exception as e:
            print(f"yt-dlp method failed: {e}")
        
        # Fallback: Use insta-api
        try:
            data = {'url': instagram_url}
            response = session.post(SCRAPING_APIS[0], data=data, headers=headers, timeout=15)
            response.raise_for_status()
            json_data = response.json()
            
            if 'url' in json_data:
                return json_data['url']
            elif 'download_url' in json_data:
                return json_data['download_url']
            elif 'data' in json_data and isinstance(json_data['data'], dict):
                if 'url' in json_data['data']:
                    return json_data['data']['url']
        except Exception as e:
            print(f"insta-api method failed: {e}")
        
        print("All video URL extraction methods failed.")
        return None
        
    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")
        return None

def convert_to_mp3(video_path, output_path):
    """Converts a video file to MP3 using pydub."""
    try:
        print(f"Reading video file: {video_path}")
        audio = AudioSegment.from_file(video_path)
        print(f"Exporting as MP3 to: {output_path}")
        audio.export(output_path, format="mp3", bitrate="192k")
        print(f"MP3 export successful")
        return True
    except FileNotFoundError:
        print("Error: FFmpeg not found. Please install FFmpeg from https://ffmpeg.org/download.html")
        return False
    except Exception as e:
        print(f"Error converting video to MP3: {e}")
        return False

@app.route('/download', methods=['POST'])
def download_and_convert():
    """Endpoint to receive URL, process, and return MP3."""
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "URL is required"}), 400

    instagram_url = data['url']
    
    # Validate Instagram URL
    if 'instagram.com' not in instagram_url:
        return jsonify({"error": "Invalid Instagram URL"}), 400
    
    video_url = get_video_url(instagram_url)

    if not video_url:
        return jsonify({"error": "Could not retrieve video URL. The link might be invalid, private, or the service is temporarily unavailable."}), 404

    video_filename = "temp_video.mp4"
    mp3_filename = "temp_audio.mp3"
    
    try:
        # Download the video
        print(f"Downloading video from: {video_url[:50]}...")
        video_response = requests.get(video_url, stream=True, timeout=30)
        video_response.raise_for_status()
        with open(video_filename, 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Convert to MP3
        print(f"Converting video to MP3...")
        if not convert_to_mp3(video_filename, mp3_filename):
            return jsonify({"error": "Failed to convert video to MP3. Make sure FFmpeg is installed."}), 500

        print("Conversion successful, sending MP3...")
        # Send the MP3 file back to the bot
        return send_file(mp3_filename, as_attachment=True, download_name='reel_audio.mp3', mimetype='audio/mpeg')

    except requests.exceptions.Timeout:
        return jsonify({"error": "Video download timed out. The video file might be too large."}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to download video: {str(e)[:100]}"}), 500
    except Exception as e:
        return jsonify({"error": f"An internal server error occurred: {str(e)[:100]}"}), 500
    finally:
        # Clean up temporary files
        if os.path.exists(video_filename):
            try:
                os.remove(video_filename)
            except:
                pass
        if os.path.exists(mp3_filename):
            try:
                os.remove(mp3_filename)
            except:
                pass

def run_flask():
    """Runs the Flask app in a separate thread."""
    # The use_reloader=False is critical when running Flask in a thread
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False, use_reloader=False)

# ==============================================================================
# --- TELEGRAM BOT (The User Interface - UPDATED FOR v20+) ---
# ==============================================================================

async def start(update: Update, context: CallbackContext) -> None:
    """Sends a message when the command /start is issued."""
    # Add a reply keyboard with a single button that prompts the user to send a reel URL
    keyboard = ReplyKeyboardMarkup(
        [["Send Reel URL"]], resize_keyboard=True
    )
    await update.message.reply_text(
        "Hello! 👋 Send me an Instagram Reel link and I'll convert it to an MP3 file for you. 🎵",
        reply_markup=keyboard,
    )

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Handles incoming messages."""
    url = update.message.text
    # If the user tapped the keyboard button, prompt them to paste the reel URL
    if url == "Send Reel URL":
        await update.message.reply_text("Please send the Instagram Reel URL.")
        return
    
    if "instagram.com/reel/" not in url:
        await update.message.reply_text("Please send a valid Instagram Reel URL.")
        return

    processing_message = await update.message.reply_text("Processing your reel... Please wait. ⏳")

    try:
        # Make a request to our LOCAL Flask server
        response = requests.post(FLASK_SERVER_URL, json={'url': url}, timeout=120)

        # Delete the "Processing..." message
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)

        if response.status_code == 200:
            # The response is the MP3 file, save it temporarily to send
            mp3_filename = "temp_result.mp3"
            with open(mp3_filename, 'wb') as f:
                f.write(response.content)
            
            # Send the audio file to the user
            with open(mp3_filename, 'rb') as audio_file:
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id, 
                    audio=audio_file,
                    title="Reel Audio"
                )
            
            # Clean up the temporary file
            os.remove(mp3_filename)

        else:
            # Try to get the error message from the Flask server's JSON response
            error_details = response.json().get("error", "Unknown server error.")
            await update.message.reply_text(f"Sorry, something went wrong.\n\nError: {error_details}")

    except requests.exceptions.RequestException as e:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)
        await update.message.reply_text(f"Could not connect to the processing server. Is it running?\n\nError: {e}")
    except Exception as e:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)
        await update.message.reply_text(f"An unexpected error occurred: {e}")

def run_bot():
    """Starts the Telegram bot."""
    if "PASTE_YOUR" in TELEGRAM_BOT_TOKEN:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! PLEASE EDIT THE SCRIPT AND ADD YOUR BOT TOKEN. !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return

    # --- UPDATED BOT INITIALIZATION ---
    # Use Application.builder() to create the bot instance
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start))
    # --- UPDATED FILTERS ---
    # Use filters.TEXT and filters.COMMAND
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    print("Telegram Bot started successfully!")
    application.run_polling()

# ==============================================================================
# --- MAIN EXECUTION ---
# ==============================================================================

if __name__ == '__main__':
    print("Starting application...")

    # Start Flask server in a separate thread
    # A daemon thread will shut down when the main program exits
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"Flask server is running in the background at {FLASK_SERVER_URL}")

    # Start the Telegram bot in the main thread
    run_bot()