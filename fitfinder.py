import os
import time
import boto3
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from serpapi import GoogleSearch

load_dotenv()

# AWS + SerpAPI setup
session = boto3.Session(profile_name="imccarty")
client = session.client("bedrock-runtime", region_name="us-west-2")
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# Streamlit session state
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("chat_messages", [])
st.session_state.setdefault("last_query_was_product_search", False)
st.session_state.setdefault("last_search_query", "")
st.session_state.setdefault("tool_results", [])

# Page Config + Custom CSS
st.set_page_config(page_title="FitFinder AI", page_icon="👗")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600&family=Satisfy&display=swap');
html, body, [class*="css"] {
    font-family: 'Quicksand', sans-serif;
    background-color: #ffeaf5 !important;
    color: #333;
    color-scheme: light !important;
}
.handwritten { font-family: 'Satisfy', cursive; }
.stChatMessage {
    background-color: white !important;
    padding: 0.75rem 1rem !important;
    border-radius: 1rem !important;
    margin-bottom: 0.5rem !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
    box-shadow: 2px 4px 10px rgba(0,0,0,0.04) !important;
    animation: fadeInMessage 0.4s ease-in-out both;
}
.stChatMessage.st-chat-message-assistant {
    background: linear-gradient(135deg, #f3e8ff, #ffe8f0) !important;
}
div[data-testid="chat-avatar"] {
    border-radius: 50% !important;
    padding: 6px !important;
    display: flex;
    align-items: center;
    justify-content: center;
}
.stChatMessage p { color: #333 !important; font-size: 16px !important; }
div[data-testid="chat-message"] { display: flex !important; align-items: center !important; }
div.stButton > button {
    background-color: #ec4899;
    color: white;
    font-weight: bold;
    border-radius: 0.5rem;
    border: none;
    padding: 0.5em 1.2em;
    margin-top: 1em;
    transition: background-color 0.3s ease;
}
div.stButton > button:hover { background-color: #db2777; }
@keyframes fadeInMessage {
    0% { opacity: 0; transform: translateY(6px); }
    100% { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    0% { opacity: 0; }
    100% { opacity: 1; }
}
</style>
""", unsafe_allow_html=True)

# Splash Screen
if "splash_shown" not in st.session_state:
    with st.spinner("🪄 Getting your closet ready..."):
        time.sleep(2.5)
    st.session_state.splash_shown = True

# Title Section
st.markdown("""
    <div style='text-align: center; animation: fadeIn 2s ease-in-out; margin-top: -1em;'>
        <h1 class='handwritten' style='font-size: 3em; color: #b83b5e;'>What Should I Wear? 👗☁️🪧</h1>
        <h4 style='color:#7a6e83; font-weight: normal;'>Let's build your look! ✨</h4>
    </div>
""", unsafe_allow_html=True)

# Tool Logic
def get_today_date_tool():
    return {"today": datetime.today().strftime("%Y-%m-%d")}

def search_tool(inputs):
    query = inputs.get("query", "")
    if not query:
        return {"results": []}
    if not SERPAPI_API_KEY:
        raise ValueError("Missing SERPAPI_API_KEY in environment variables.")

    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "gl": "us",
        "hl": "en",
        "google_domain": "google.com",
        "device": "desktop",
        "direct_link": True
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    shopping_items = results.get("shopping_results", [])

    top_results = [{
        "title": item.get("title"),
        "price": item.get("price"),
        "link": item.get("link") or item.get("product_link"),
        "source": item.get("source"),
        "thumbnail": item.get("thumbnail")
    } for item in shopping_items[:3]]

    st.session_state.last_query_was_product_search = True
    st.session_state.last_search_query = query

    return {"results": top_results}

tool_config = {
    "tools": [
        {"toolSpec": {
            "name": "get_today_date",
            "description": "Returns today's date.",
            "inputSchema": {"json": {"type": "object", "properties": {}, "required": []}}
        }},
        {"toolSpec": {
            "name": "search_tool",
            "description": "Fashion product search",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        }}
    ],
    "toolChoice": {"auto": {}}
}

def run_tool(name, inputs):
    if name == "get_today_date":
        return get_today_date_tool()
    elif name == "search_tool":
        return search_tool(inputs)
    raise ValueError(f"Unknown tool: {name}")

def ask_bedrock(user_input):
    messages = [{
        "role": "user",
        "content": [{
            "text": (
                "You're a fashion assistant. When someone asks what to wear, first ask 2–3 follow-up questions "
                "to clarify the event type, style, weather, time of day, or budget. Only use search_tool after clarification. "
                "After recommending outfits, suggest next steps like accessories, outerwear, or shoes."
            )
        }]
    }] + st.session_state.chat_messages

    messages.append({"role": "user", "content": [{"text": user_input}]})

    while True:
        res = client.converse(
            modelId=model_id,
            messages=messages,
            toolConfig=tool_config
        )

        output_msg = res["output"]["message"]
        messages.append(output_msg)

        tool_use = next((b["toolUse"] for b in output_msg["content"] if "toolUse" in b), None)
        if tool_use:
            result_data = run_tool(tool_use["name"], tool_use["input"])
            messages.append({
                "role": "user",
                "content": [{
                    "toolResult": {
                        "toolUseId": tool_use["toolUseId"],
                        "content": [{"json": result_data}],
                        "status": "success"
                    }
                }]
            })
            st.session_state["tool_results"].append((len(st.session_state.chat_history), result_data))
            continue

        return messages[-1]

# Main UI
user_input = st.chat_input("What's the vibe? Type your event, style, or color aesthetic ✨", key="chatbox")

if user_input:
    st.session_state.chat_history.append({"role": "user", "text": user_input})
    reply = ask_bedrock(user_input)
    for content in reply["content"]:
        if "text" in content:
            st.session_state.chat_history.append({"role": "assistant", "text": content["text"]})
        elif "toolUse" in content:
            st.session_state.chat_history.append({"role": "assistant", "text": "[Searching for stylish options...]"})
    st.session_state.chat_messages.append(reply)

# Chat display + result inline rendering
for i, msg in enumerate(st.session_state.chat_history):
    st.chat_message(msg["role"]).markdown(msg["text"])
    for result_index, result_block in st.session_state.get("tool_results", []):
        if result_index == i:
            results = result_block.get("results", [])
            if results:
                st.markdown("### 🍭 Styled Picks Just for You")
                for product in results:
                    st.image(product["thumbnail"], width=200)
                    st.markdown(f"**[{product['title']}]({product['link']})**")
                    st.markdown(f"💰 {product['price']} &nbsp;&nbsp;|   🛍️ *{product['source']}*")
                    st.markdown("---")

# Accessories button
if st.session_state.get("last_query_was_product_search", False):
    if st.button("Show me accessories for this outfit"):
        accessory_prompt = (
            "Can you suggest matching accessories like jewelry, bags, or shoes to complete the outfits? "
            "Only show accessories, not clothes."
        )
        st.session_state.chat_history.append({"role": "user", "text": accessory_prompt})
        reply = ask_bedrock(accessory_prompt)
        for content in reply["content"]:
            if "text" in content:
                st.session_state.chat_history.append({"role": "assistant", "text": content["text"]})
            elif "toolUse" in content:
                st.session_state.chat_history.append({"role": "assistant", "text": "[Searching for accessories...]"})
        st.session_state.chat_messages.append(reply)
        st.session_state.last_query_was_product_search = False

# Footer
st.markdown("""
    <hr style="margin-top: 2em; margin-bottom: 1em; border: none; border-top: 1px solid #f4c2d7;" />
    <div style="text-align: center; color: #b83b5e; font-size: 0.9em; font-family: 'Quicksand', sans-serif;">
        Built by Sam and Bella 💖
    </div>
""", unsafe_allow_html=True)