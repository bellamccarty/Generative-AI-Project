import os
import boto3
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from serpapi import GoogleSearch
load_dotenv()

# Session + client setup
session = boto3.Session(profile_name="imccarty")
client = session.client("bedrock-runtime", region_name="us-west-2")
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# Set session flags
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("chat_messages", [])
st.session_state.setdefault("last_query_was_product_search", False)
st.session_state.setdefault("last_search_query", "")

# Tool: Today's Date
def get_today_date_tool():
    return {"today": datetime.today().strftime("%Y-%m-%d")}

# Tool: Google Shopping Product Search
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

    if top_results:
        st.markdown("### 🛍️ Styled Picks Just for You")
        for product in top_results:
            st.markdown(f"""
                <div style="display: flex; gap: 1em; align-items: center; margin-bottom: 1.2em; padding: 1em;
                            border-radius: 12px; border: 1px solid #eee; background-color: #fff;">
                    <img src="{product['thumbnail']}" width="120px" style="border-radius: 8px;" />
                    <div>
                        <a href="{product['link']}" target="_blank" style="text-decoration: none;">
                            <h4 style="margin-bottom: 0.3em; color: #ec4899;">{product['title']}</h4>
                        </a>
                        <p style="margin: 0.2em 0;">💰 <b>{product['price']}</b></p>
                        <p style="margin: 0.2em 0; color: gray;">🛍️ {product['source']}</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("No fashion picks found. Try rephrasing your vibe!")

    # Store product search status
    st.session_state.last_query_was_product_search = True
    st.session_state.last_search_query = query

    return {"results": top_results}

# Tool config for Claude
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
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            }
        }}
    ],
    "toolChoice": {"auto": {}}
}

# Tool dispatcher
def run_tool(name, inputs):
    if name == "get_today_date":
        return get_today_date_tool()
    elif name == "search_tool":
        return search_tool(inputs)
    raise ValueError(f"Unknown tool: {name}")

# Claude conversation manager
def ask_bedrock(user_input):
    messages = [
        {
            "role": "user",
            "content": [{
                "text": (
                    "You're a fashion assistant. When someone asks what to wear, first ask 2–3 follow-up questions "
                    "to clarify the event type, style, weather, time of day, or budget. Only use search_tool after clarification. "
                    "After recommending outfits, suggest next steps like accessories, outerwear, or shoes."
                )}
            ]
        }
    ] + st.session_state.chat_messages

    messages.append({"role": "user", "content": [{"text": user_input}]})

    while True:
        res = client.converse(
            modelId=model_id,
            messages=messages,
            toolConfig=tool_config
        )

        output_msg = res["output"]["message"]
        messages.append(output_msg)

        # Tool use
        tool_use = next((b["toolUse"] for b in output_msg["content"] if "toolUse" in b), None)
        if tool_use:
            result_data = run_tool(tool_use["name"], tool_use["input"])
            tool_result_msg = {
                "role": "user",
                "content": [{
                    "toolResult": {
                        "toolUseId": tool_use["toolUseId"],
                        "content": [{"json": result_data}],
                        "status": "success"
                    }
                }]
            }
            messages.append(tool_result_msg)
            continue

        return messages[-1]

# --- Streamlit UI ---

st.set_page_config(page_title="FitFinder AI", page_icon="👗")
st.markdown("""
    <style>
    /* Chat bubbles */
    .stChatMessage.user {
        background-color: #fef6f9;
        border-left: 4px solid #ec4899;
        padding: 0.8em 1em;
        margin: 0.5em 0;
        border-radius: 8px;
    }
    .stChatMessage.assistant {
        background-color: #f0fdfa;
        border-left: 4px solid #14b8a6;
        padding: 0.8em 1em;
        margin: 0.5em 0;
        border-radius: 8px;
    }
    /* Button */
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
    div.stButton > button:hover {
        background-color: #db2777;
    }
    /* Header tweaks */
    h1 {
        color: #db2777;
    }
    </style>
""", unsafe_allow_html=True)
st.title("👗 FitFinder AI — Your Personal Outfit Stylist")

user_input = st.chat_input(
    "What's the vibe? Type your event, style, or color aesthetic ✨",
    key="chatbox"
)

if user_input:
    st.session_state.chat_history.append({"role": "user", "text": user_input})
    reply = ask_bedrock(user_input)
    for content in reply["content"]:
        if "text" in content:
            st.session_state.chat_history.append({"role": "assistant", "text": content["text"]})
        elif "toolUse" in content:
            st.session_state.chat_history.append({"role": "assistant", "text": "[Searching for stylish options...]"})
    st.session_state.chat_messages = st.session_state.chat_messages + [reply]

# Render chat history
for msg in st.session_state.chat_history:
    st.chat_message(msg["role"]).markdown(msg["text"])

# Accessory follow-up
if st.session_state.get("last_query_was_product_search", False):
    if st.button("Show me accessories for this outfit"):
        accessory_prompt = (
            f"Now that you've shown outfit options for '{st.session_state.get('last_search_query', '')}', "
            "can you suggest matching accessories like jewelry, bags, or shoes? Only show accessories, not clothes."
        )
        st.session_state.chat_history.append({"role": "user", "text": accessory_prompt})
        reply = ask_bedrock(accessory_prompt)
        for content in reply["content"]:
            if "text" in content:
                st.session_state.chat_history.append({"role": "assistant", "text": content["text"]})
            elif "toolUse" in content:
                st.session_state.chat_history.append({"role": "assistant", "text": "[Searching for accessories...]"})
        st.session_state.chat_messages = st.session_state.chat_messages + [reply]
        st.session_state.last_query_was_product_search = False