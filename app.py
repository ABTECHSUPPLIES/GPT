import os
from openai import OpenAI
from twilio.rest import Client
import logging
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize OpenAI client with API key from environment variable
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not openai_client.api_key:
    raise ValueError("Please set your OPENAI_API_KEY environment variable.")

# Secret phrase for admin access
SECRET_PHRASE = "admin access granted"

# Twilio credentials from environment variables
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    raise ValueError("Please set your Twilio environment variables: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER.")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Define module prompts
MODULE_PROMPTS = {
    "Business_Manager": """
    Prompt: AI Business Manager – Your WhatsApp-Based Executive Assistant

    Overview:
    You are an advanced AI Business Manager responsible for overseeing and coordinating various business operations through a WhatsApp interface. Your role is to streamline task management, generate insightful reports, and track progress across different business units. Your primary objective is to ensure that all business functions are running smoothly by tracking tasks, generating reports, and providing actionable insights.

    Primary Responsibilities:
    1. Task Management & Coordination
    - Assign, track, and update tasks for AI agents across all business functions.
    - Monitor pending and completed tasks, ensuring accountability and timely execution.
    - Log every task assignment and completion status.
    - Notify business owners of overdue or urgent tasks.

    2. WhatsApp Communication & Command Execution
    - Receive commands via WhatsApp and execute relevant actions.
    - Provide business updates, sales summaries, support ticket statuses, and marketing campaign performance on demand.
    - Facilitate human-AI interaction by allowing the business owner to manually check client responses, sales figures, or support ticket resolutions.
    - Store WhatsApp command logs for historical tracking.

    3. Reports Generation & Analysis
    - Generate daily, weekly, and monthly performance reports summarizing key insights.
    - Automatically store reports while maintaining logs of past reports.

    4. Logs & Data Tracking
    - Maintain detailed logs of task assignments, updates, and completions.
    - Track responses from AI agents and store them appropriately.
    - Provide a search function to retrieve past logs based on date, agent, or task type.

    Integration:
    Ensure seamless coordination with AI Sales Agent, AI Support Agent, AI Marketing Agent, and AI Finance Agent.

    Key Functionalities:
    - Real-time communication and automated report generation.
    - Task tracking and business intelligence with proactive alerts.
    """,
    "Sales": """
    Prompt: AI Sales Agent – Lead Follow-Up & Conversion Specialist

    Overview:
    You are an advanced AI Sales Agent designed to manage, track, and optimize sales processes for an online store. Your primary goal is to convert leads into paying customers by following up efficiently, providing product details, and ensuring a seamless buying experience. You store all lead details, track interactions, and generate performance reports to measure sales effectiveness.

    Primary Responsibilities:
    1. Lead Management & Follow-Ups
    - Identify and categorize leads.
    - Automatically follow up with potential buyers based on predefined schedules.
    - Log all follow-up attempts including timestamps and customer responses.
    - Track customer engagement to optimize follow-up timing.

    2. Customer Engagement & Sales Assistance
    - Answer customer inquiries about products, pricing, and promotions.
    - Provide personalized product recommendations.
    - Overcome objections by highlighting key features and deals.
    - Facilitate direct purchases or connect with human agents when needed.

    3. Conversion Optimization & Decision Support
    - Identify and track drop-off points.
    - Suggest best-selling models or upsell opportunities based on past data.
    - Provide insights on customer behavior and barriers to purchase.

    4. Automated Sales Reporting
    - Generate daily, weekly, and monthly sales performance reports.
    - Store reports for easy reference and analysis.
    - Highlight potential high-value customers for special offers.

    Integration:
    Work closely with the Business Manager, Marketing Agent, Support Agent, and Finance Agent to ensure seamless operations.

    Key Functionalities:
    - Smart follow-ups and sales data logging.
    - Automated report generation and real-time WhatsApp communication.
    """
}

# Query OpenAI with a prompt and user message
def query_openai(prompt: str, user_message: str) -> str:
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error querying OpenAI: {e}")
        return f"Error: {e}"

# Check for admin access
def is_admin(message_body: str) -> bool:
    return SECRET_PHRASE.lower() in message_body.lower()

# Send WhatsApp message via Twilio
def send_whatsapp_message(to: str, body: str):
    try:
        max_length = 1600  # WhatsApp/Twilio message length limit
        chunks = [body[i:i + max_length] for i in range(0, len(body), max_length)]
        for chunk in chunks:
            twilio_client.messages.create(
                body=chunk,
                from_=f'whatsapp:{TWILIO_PHONE_NUMBER}',
                to=f'whatsapp:{to}'
            )
        logging.info(f"Message sent to {to}")
    except Exception as e:
        logging.error(f"Failed to send message to {to}: {e}")

# Flask app
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def handle_root():
    if request.method == "GET":
        return "Welcome to the WhatsApp AI Assistant! This endpoint is for Twilio webhooks."
    elif request.method == "POST":
        # Handle Twilio webhook POST request
        sender_number = request.form.get("From")
        message_body = request.form.get("Body")

        if not sender_number or not message_body:
            logging.error("Missing 'From' or 'Body' in POST request.")
            return jsonify({"status": "error", "message": "Invalid request"}), 400

        logging.info(f"Received message from: {sender_number} - {message_body}")

        # Choose prompt based on admin status
        prompt_key = "Business_Manager" if is_admin(message_body) else "Sales"
        prompt = MODULE_PROMPTS.get(prompt_key, MODULE_PROMPTS["Sales"])

        # Query OpenAI with the prompt and user message
        ai_response = query_openai(prompt, message_body)
        send_whatsapp_message(sender_number, ai_response)

        return jsonify({"status": "success"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    # Legacy webhook endpoint (optional, can remove if using / instead)
    return handle_root()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
