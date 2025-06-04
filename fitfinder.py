import os
import boto3
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from serpapi import GoogleSearch
load_dotenv()

# Set up Bedrock client
session = boto3.Session(profile_name="imccarty")
client = session.client("bedrock-runtime", region_name="us-west-2")
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# Tool: Today's Date
def get_today_date_tool():
    st.write("### Using the tool `get_today_date`")
    res = {"today": datetime.today().strftime("%Y-%m-%d")}
    st.markdown("Tool Result")
    st.markdown(res)
    st.markdown("---")
    return res

# Tool: Fashion-forward Search via SerpAPI
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

    # ⬇️ Clean visual output for the Streamlit UI
    if top_results:
        st.markdown("### 🛍️ Styled Picks Just for You")
        for product in top_results:
            st.image(product["thumbnail"], width=200)
            st.markdown(f"**[{product['title']}]({product['link']})**")
            st.markdown(f"💰 {product['price']} &nbsp;&nbsp;|&nbsp;&nbsp; 🛍️ *{product['source']}*")
            st.markdown("---")
    else:
        st.warning("No fashion picks found. Try rephrasing your vibe!")

    return {"results": top_results}

# Tool config specs
datetime_tool_spec = {
    "name": "get_today_date",
    "description": "Returns today's date in YYYY-MM-DD format. Always use this to understand time. Use it before searching any current events.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

search_tool_spec = {
    "name": "search_tool",
    "description": "Uses SerpAPI to return current fashion-forward shopping results. Useful for outfit planning, styling, or trend-based recommendations.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    }
}

tool_config = {
    "tools": [{"toolSpec": datetime_tool_spec}, {"toolSpec": search_tool_spec}],
    "toolChoice": {"auto": {}}
}

# Tool routing function
def run_tool(name, inputs):
    if name == "get_today_date":
        return get_today_date_tool()
    elif name == "search_tool":
        return search_tool(inputs)
    raise ValueError(f"Unknown tool: {name}")

# Core function that sends prompt to Claude and handles tool calls
def ask_bedrock(prompt):
    messages = [
        {
            "role": "user",
            "content": [{"text": prompt}]
        }
    ]

    while True:
        res = client.converse(
            modelId=model_id,
            messages=messages,
            toolConfig=tool_config
        )

        output_msg = res["output"]["message"]
        messages.append(output_msg)

        # Check if Claude wants to use a tool
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

        return messages

# Streamlit UI
st.title("👗 FitFinder AI — What Should I Wear?")

user_input = st.text_area(
    "Describe your event or vibe:",
    placeholder="e.g. Rooftop dinner in red, or Coachella day look in pastels"
)

if st.button("Get Outfit Ideas"):
    with st.spinner("Consulting fashion oracle..."):
        _ = ask_bedrock(user_input)