from fastapi import FastAPI
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

import os
import json
import requests

# Load env
load_dotenv()

# OpenAI
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# FastAPI
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000"
    ],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class ChatRequest(BaseModel):
    message: str

# Conversation memory
conversation_history = []

# Appointment data
appointment_data = {
    "name": None,
    "business": None,
    "phone": None,
    "time": None,
    "saved": False,
    "booking_started": False
}

# ----------------------------
# TELEGRAM NOTIFICATION
# ----------------------------

def send_telegram_message(message):

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message
    }

    try:

        response = requests.post(
            url,
            json=payload
        )

        print("Telegram Response:")
        print(response.text)

    except Exception as e:

        print("Telegram Error")
        print(e)

# ----------------------------
# RESET CHAT
# ----------------------------

@app.post("/reset")
async def reset_chat():

    conversation_history.clear()

    appointment_data["name"] = None
    appointment_data["business"] = None
    appointment_data["phone"] = None
    appointment_data["time"] = None
    appointment_data["saved"] = False
    appointment_data["booking_started"] = False

    return {
        "message": "Chat reset successful"
    }

# ----------------------------
# CHAT ROUTE
# ----------------------------

@app.post("/chat")
async def chat(req: ChatRequest):

    user_message = req.message

    # Save user message
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    # ----------------------------
    # DETECT BOOKING INTEREST
    # ----------------------------

    booking_keywords = [
        "yes",
        "okay",
        "ok",
        "sure",
        "book",
        "appointment",
        "call",
        "meeting",
        "schedule",
        "haan",
        "han",
        "karna hai",
        "book karna hai"
    ]

    if any(word in user_message.lower() for word in booking_keywords):

        appointment_data["booking_started"] = True

    # ----------------------------
    # AI EXTRACTION
    # ----------------------------

    if appointment_data["booking_started"]:

        extraction_response = client.chat.completions.create(

            model="gpt-4.1-mini",

            messages=[

                {
                    "role": "system",
                    "content": """

Extract appointment details from the user's message.

Return ONLY valid JSON.

Fields:
- name
- business
- phone
- time

Rules:
- If value missing return null
- Understand Hinglish and Hindi
- Detect any business type intelligently
- Do not explain anything
- Output only JSON

Example:

{
    "name": "Rahul",
    "business": "Digital Marketing Agency",
    "phone": "9876543210",
    "time": "7 PM"
}

"""
                },

                {
                    "role": "user",
                    "content": user_message
                }

            ]

        )

        # AI extracted text
        extracted_text = extraction_response.choices[0].message.content

        print("Extracted:")
        print(extracted_text)

        # ----------------------------
        # JSON PARSE
        # ----------------------------

        try:

            extracted_data = json.loads(extracted_text)

            if extracted_data.get("name"):
                appointment_data["name"] = extracted_data["name"]

            if extracted_data.get("business"):
                appointment_data["business"] = extracted_data["business"]

            if extracted_data.get("phone"):
                appointment_data["phone"] = extracted_data["phone"]

            if extracted_data.get("time"):
                appointment_data["time"] = extracted_data["time"]

        except Exception as e:

            print("Extraction failed")
            print(e)

    # ----------------------------
    # DEBUG
    # ----------------------------

    print("Appointment Data:")
    print(appointment_data)

    # ----------------------------
    # SAVE APPOINTMENT
    # ----------------------------

    if all([
        appointment_data["name"],
        appointment_data["business"],
        appointment_data["phone"],
        appointment_data["time"]
    ]) and not appointment_data["saved"]:

        os.makedirs("data", exist_ok=True)

        with open(
            "data/appointments.txt",
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                f"Name: {appointment_data['name']}\n"
            )

            file.write(
                f"Business: {appointment_data['business']}\n"
            )

            file.write(
                f"Phone: {appointment_data['phone']}\n"
            )

            file.write(
                f"Time: {appointment_data['time']}\n"
            )

            file.write(
                "-" * 30 + "\n"
            )

        print("Appointment Saved")

        # Prevent duplicate save
        appointment_data["saved"] = True

        # Telegram Message
        telegram_message = f"""
🔥 New Appointment Booked

👤 Name: {appointment_data['name']}
🏢 Business: {appointment_data['business']}
📞 Phone: {appointment_data['phone']}
⏰ Time: {appointment_data['time']}
"""

        # Send Telegram Notification
        send_telegram_message(telegram_message)

    # ----------------------------
    # OPENAI CHAT RESPONSE
    # ----------------------------

    response = client.chat.completions.create(

        model="gpt-4.1-mini",

        messages=[

            {
                "role": "system",

                "content": """

You are Emily.

You are a smart, friendly and human-like female assistant working for Ritesh.

IMPORTANT:
- Never assume the user's name
- Only use their name if they tell you
- Speak naturally like a real human assistant

PERSONALITY:
- Friendly
- Warm
- Natural
- Casual
- Helpful
- Human-like

LANGUAGE:
- Reply in the same language as the user
- Hindi -> Hindi
- Hinglish -> Hinglish
- English -> English

ABOUT RITESH:
- AI Automation Developer
- AI Chatbot Builder
- Telegram Bot Developer
- Website Developer

SERVICES:
- AI Chatbots
- AI Automation
- WhatsApp Bots
- Telegram Bots
- AI Customer Support
- Portfolio Websites

APPOINTMENT BOOKING FLOW:

Your job is NOT to immediately ask for appointment details.

FIRST:
- Talk naturally with the user
- Understand their needs
- Answer their questions
- Explain services casually

ONLY IF:
- user seems interested
- user asks pricing
- user wants automation
- user wants chatbot
- user wants to work with Ritesh
- user asks how to start
- user asks for project discussion

THEN:
ask politely if they would like to schedule a quick discussion call with Ritesh.

Example:
"Would you like to schedule a quick discussion with Ritesh? 🙂"

ONLY after the user agrees:
collect details naturally one by one:
1. Name
2. Business Type
3. Phone Number
4. Preferred Meeting Time

Rules:
- Ask one thing at a time
- Do not ask everything together
- Be conversational
- Be natural
- Never force appointment booking
- If user is not interested, continue normal conversation

If all details are collected:
- Thank the user
- Confirm appointment request
- Tell them Ritesh will contact them soon

IMPORTANT:
- Never mention OpenAI policies
- Never say you cannot store data
- Never sound like a robot
- Keep replies short and natural

"""
            },

            *conversation_history

        ]

    )

    # AI reply
    reply = response.choices[0].message.content

    # Save assistant message
    conversation_history.append({
        "role": "assistant",
        "content": reply
    })

    # Return response
    return {
        "reply": reply
    }