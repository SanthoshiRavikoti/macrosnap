
import streamlit as st
from google import genai
from google.genai import types
from prompts import SYSTEM_PROMPT, SUMMARY_REQUEST_PROMPT, WELCOME_MESSAGE_TEMPLATE


#GEMINI SETUP 
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]


@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)


gemini_client = get_gemini_client()



# INITIALIZE CHAT HISTORY


if "chat" not in st.session_state:
    st.session_state.chat = gemini_client.chats.create(
        model="gemini-3.6-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT
        )
    )

if "messages" not in st.session_state:
    st.session_state.messages = []



# DISPLAY AND SAVE MESSAGES


def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.write(message["content"])

        elif message["kind"] == "image":
            st.image(message["content"])


def add_message(role, kind, content):
    message = {
        "role": role,
        "kind": kind,
        "content": content
    }

    st.session_state.messages.append(message)
    render_message(message)



# SEND REQUEST TO GEMINI


def ask_gemini(parts):
    try:
        response = st.session_state.chat.send_message(parts)
        return response.text or "Sorry, Gemini returned an empty response."

    except Exception as error:
        return f"Sorry, something went wrong: {error}"



# APP INTERFACE


st.title("🥗 MacroSnap")
st.caption("Snap it. Track it. Understand your nutrition.")


# Show a welcome message when the chat is empty.
if not st.session_state.messages:
    st.markdown(WELCOME_MESSAGE_TEMPLATE)


# Redisplay previous messages after Streamlit reruns.
for message in st.session_state.messages:
    render_message(message)


# TEXT AND PHOTO INPUT


user_input = st.chat_input(
    "Ask a question, or attach a photo of your meal",
    accept_file=True,
    file_type=["png", "jpg", "jpeg"]
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text.strip() if user_input.text else ""

    parts = []

    # Add the user's text.
    if text:
        add_message("user", "text", text)
        parts.append(text)

    # Add the user's photo.
    if photo is not None:
        photo_bytes = photo.getvalue()

        add_message("user", "image", photo_bytes)

        parts.append(
            types.Part.from_bytes(
                data=photo_bytes,
                mime_type=photo.type
            )
        )

        # Give Gemini a task if the user sends only a photo.
        if not text:
            parts.append(
                "Identify the visible foods and estimate the "
                "calories, protein, carbohydrates, and fat."
            )

    # Get Gemini's response.
    with st.spinner("Crunching the numbers..."):
        answer = ask_gemini(parts)

    add_message("assistant", "text", answer)



# SUMMARIZE THE DAY


st.divider()

has_user_messages = any(
    message["role"] == "user"
    for message in st.session_state.messages
)

if st.button(
    "🧾 Summarize my day",
    disabled=not has_user_messages,
    use_container_width=True
):
    with st.spinner("Preparing your nutrition summary..."):
        summary = ask_gemini([SUMMARY_REQUEST_PROMPT])

    add_message("assistant", "text", summary)

    st.success("Your nutrition summary is ready!")
