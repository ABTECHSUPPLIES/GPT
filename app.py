import os
import openai
from twilio.rest import Client
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load your OpenAI API key from an environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("Please set your OPENAI_API_KEY environment variable.")

# Secret phrase for admin access
SECRET_PHRASE = "admin access granted"

# Twilio credentials and settings
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    raise ValueError("Please set your Twilio environment variables.")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Define all module prompts in a dictionary.
MODULE_PROMPTS = {
    "Business_Manager": """
    Prompt: AI Business Manager – Your WhatsApp-Based Executive Assistant
    Overview: You are an advanced AI Business Manager responsible for overseeing and coordinating various business operations through a WhatsApp interface.
    """,
    "Sales": """
    Prompt: AI Sales Agent – Lead Follow-Up & Conversion Specialist
    Overview: You are an advanced AI Sales Agent designed to manage, track, and optimize sales processes for an online store.
    """,
}

# Query OpenAI GPT-4
def query_openai(prompt_text: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": prompt_text}],
            temperature=0.7,
            max_tokens=1000,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"An error occurred while querying OpenAI: {e}")
        return f"An error occurred: {e}"

# Check if the message body contains the secret phrase to grant admin access
def is_admin(message_body: str) -> bool:
    return SECRET_PHRASE.lower() in message_body.lower()

# Send WhatsApp message using Twilio
def send_whatsapp_message(to, body):
    try:
        max_length = 1600
        chunks = [body[i:i+max_length] for i in range(0, len(body), max_length)]

        for chunk in chunks:
            twilio_client.messages.create(
                body=chunk,
                from_=f'whatsapp:{TWILIO_PHONE_NUMBER}',
                to=f'whatsapp:{to}'
            )
        logging.info(f"Message sent successfully to {to}")
    except Exception as e:
        logging.error(f"Failed to send message to {to}: {e}")

# Flask app to handle incoming messages
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Welcome to the service! This is the home page."

@app.route("/webhook", methods=["POST"])
def webhook():
    sender_number = request.form.get("From")
    message_body = request.form.get("Body")

    if not sender_number or not message_body:
        logging.error("Missing 'From' or 'Body' in the request.")
        return jsonify({"status": "error", "message": "Invalid request"}), 400

    logging.info(f"Received message from: {sender_number}")

    # Check for admin access
    prompt_key = "Business_Manager" if is_admin(message_body) else "Sales"
    prompt = MODULE_PROMPTS.get(prompt_key, "Sales")
    
    ai_response = query_openai(prompt)
    send_whatsapp_message(sender_number, ai_response)

    return jsonify({"status": "success"})

if __name__ == "__main__":
    # Use production server in production environment (e.g., gunicorn)
    app.run(host="0.0.0.0", port=5000, debug=True)
