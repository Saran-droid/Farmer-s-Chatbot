from flask import Flask, request, jsonify, session
from flask_cors import CORS
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import ChatMessageHistory
import requests
import os
from dotenv import load_dotenv
import secrets
import pandas as pd
from translate import translate_back,detect_language_and_translate
import traceback
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.secret_key = secrets.token_hex(32)

@app.before_request
def ensure_session_id():
    if "user_id" not in session:
        session["user_id"] = secrets.token_hex(8)

API_KEY = os.getenv("api")
URL = "https://openrouter.ai/api/v1/chat/completions"

user_memories = {}


def get_market_price(commodity, state):
    api_url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    api_key = "579b464db66ec23bdd0000017399cbbbcdfa499976391b977d7487fe"

    params = {
        "api-key": api_key,
        "format": "json",
        "filters[commodity]": commodity,
        "filters[state]": state,
        "limit": 150
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()

        if "records" in data and data["records"]:
            result = []
            for record in data["records"]:
                result.append(f"Market: {record['market']}, Price: {record['modal_price']} Rs/quintal, Date: {record['arrival_date']}")
            return "\n".join(result)
        else:
            return "No data found for the given commodity and state."

    except requests.exceptions.RequestException as e:
        return f"Error fetching data: {e}"


# **AI-Powered Query Classification & Follow-Up Detection**
def classify_user_query_with_context(user_query, previous_context, model="mistralai/mistral-7b-instruct:free", temperature=0.7):
    """
    Classifies a user query into predefined farming-related categories using OpenRouter's AI model.
    Now also extracts the state name if present.
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f'''Analyze the conversation and classify the latest query.

              Conversation History:
              {previous_context}

              New User Query:
              "{user_query}"

              Tasks:
              1. Is this query a **follow-up** to a previous one? (YES/NO)
              2. If YES, summarize what it is referring to.
              3. Classify the query into one or more of the following categories (choose multiple if applicable):
                  - Market Price
                  - Pest Control
                  - Fertilizer Recommendation
                  - General Farming Information
                  - Pesticide and Related Explanation
                  - Irrelevant
              4. Extract the **crop name** mentioned (or return "None").
              5. Extract the **state name** mentioned (or return "None"). 

              Important Notes:
              - If the query asks about **market price**, ensure the state is included if mentioned.
              - If uncertain, prefer a broader category rather than misclassifying.

              Response Format:
              Follow-Up: <YES/NO>
              Context: <Brief Summary>
              Category: <Predicted Category(should be a single category)>
              Crop: <Crop Name (or "None")>
              State: <State Name (or "None")>
              '''

    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature
    }

    try:

        response = requests.post(URL, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        print(response_json)
        if "choices" in response_json and response_json["choices"]:
            print("Hi")
            return response_json["choices"][0]["message"]["content"]

        return "Error: No valid response from API"

    except requests.exceptions.RequestException as e:
        return f"API Request Error: {str(e)}"



# **AI-Powered General Farming Question Answering**
def answer_general_farming_question(user_query, previous_context, model="meta-llama/llama-3.2-1b-instruct:free", temperature=0.7):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f'''You are an expert farming assistant. Answer the following question accurately.

    **Conversation History:**
    {previous_context}  

    **User Question:**
    "{user_query}"

    **Provide a helpful and detailed farming-related answer.**
    '''

    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature
    }

    try:
        response = requests.post(URL, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()

        if "choices" in response_json and response_json["choices"]:
            return response_json["choices"][0]["message"]["content"]

        return "Error: No valid response from API"

    except requests.exceptions.RequestException as e:
        return f"API Request Error: {str(e)}"


def fetch_pesticide_recommendations(crop):
    """
    Fetch the recommended pesticides for a given crop.

    Parameters:
    crop (str): The name of the crop.

    Returns:
    str: A list of recommended pesticides or a message if the crop is not found.
    """
    # Load the CSV file
    df = pd.read_csv("Fert&Pest.csv")

    # Standardize column names to avoid issues
    df.columns = df.columns.str.strip()

    # Search for the crop in the Commodity column (case-insensitive)
    result = df[df["Commodity"].str.lower() == crop.lower().strip()]

    if not result.empty:
        return result["Pesticides"].values[0]  # Return the pesticides for the given crop
    else:
        return f"No pesticide recommendations found for {crop}."


def fetch_fertilizer_recommendations(crop):
    """
    Fetch the recommended fertilizers for a given crop.

    Parameters:
    crop (str): The name of the crop.

    Returns:
    str: A list of recommended fertilizers or a message if the crop is not found.
    """
    # Load the CSV file
    df = pd.read_csv("Fert&Pest.csv")

    # Standardize column names to avoid issues
    df.columns = df.columns.str.strip()

    # Search for the crop in the Commodity column (case-insensitive)
    result = df[df["Commodity"].str.lower() == crop.lower().strip()]

    if not result.empty:
        return result["Fertilizers"].values[0]  # Return the fertilizers for the given crop
    else:
        return f"No fertilizer recommendations found for {crop}."

# **User Query Handling**




def get_user_memory():
    user_id = session.get("user_id")
    if not user_id:
        user_id = secrets.token_hex(8)
        session["user_id"] = user_id
    if user_id not in user_memories:
        history = ChatMessageHistory()
        user_memories[user_id] = ConversationBufferMemory(chat_memory=history, return_messages=True)
    return user_memories[user_id]


def handle_user_query(user_query):
    print("\n🔹 New User Query Received:", user_query)

    memory = get_user_memory()

    # Detect language and translate to English
    try:
        detected_lang, translated_query = detect_language_and_translate(user_query)
        print(f"🌍 Language Detected: {detected_lang} | Translated Query: {translated_query}")
    except Exception as e:
        print(f"🚨 Language Detection Error: {traceback.format_exc()}")
        return "Error in language detection or translation."

    # Load chat history
    try:
        chat_history = memory.load_memory_variables({})
        previous_context = "\n".join([msg.content for msg in chat_history.get("history", [])])
        print(f"📜 Chat History Loaded: {previous_context}")
    except Exception as e:
        print(f"🚨 Chat History Load Error: {traceback.format_exc()}")
        previous_context = ""

    # Store queries in a single input key (Fix for Memory Issue)
    combined_input = f"Original: {user_query}\nTranslated: {translated_query}"

    try:
        memory.save_context({"input": combined_input}, {"output": "Processing..."})
    except Exception as e:
        print(f"🚨 Memory Save Error (Initial): {traceback.format_exc()}")

    # Classify query
    try:
        classification_result = classify_user_query_with_context(translated_query, previous_context)
        print(f"🔍 Classification Result: {classification_result}")
        if not classification_result:
            raise ValueError("Classification failed; no result returned.")
    except Exception as e:
        print(f"🚨 Classification Error: {traceback.format_exc()}")
        return "Error in classifying the query."

    # Default values
    is_follow_up, follow_up_context, category, crop, state = "NO", "None", "Unknown", "None", "None"

    # Extract values from classification
    try:
        if "Follow-Up:" in classification_result and "Category:" in classification_result:
            is_follow_up = classification_result.split("Follow-Up:")[1].split("\n")[0].strip()
            follow_up_context = classification_result.split("Context:")[1].split("\n")[0].strip()
            category = classification_result.split("Category:")[1].split("\n")[0].strip()
            crop = classification_result.split("Crop:")[1].split("\n")[0].strip()
            state = classification_result.split("State:")[1].split("\n")[0].strip()

        print(f"📝 Extracted Info: Follow-Up: {is_follow_up}, Category: {category}, Crop: {crop}, State: {state}")
    except IndexError:
        print(f"⚠️ Error parsing classification result: {classification_result}")

    response_parts = []

    # Handle Queries Based on Classification
    try:
        if "Market Price" in category:
            print(f"💰 Fetching Market Price for {crop} in {state}")
            if crop.lower() == "none":
                response_parts.append("Please specify the **crop name** to get market prices.")
            elif state.lower() == "none":
                response_parts.append("Please specify the **state** to get market prices.")
            else:
                market_price_info = get_market_price(crop, state)
                print(f"✅ Market Price API Response: {market_price_info}")
                response_parts.append(f"**Market Price for {crop} in {state}:**\n{market_price_info}")

        elif "Pesticide and Related Explanation" in category:
            print(f"🐛 Fetching Pesticide Recommendations for {crop}")
            general_info = answer_general_farming_question(translated_query, previous_context)
            pesticide_info = fetch_pesticide_recommendations(crop)

            response_parts.append(f"**Farming Expert's Advice:**\n{general_info}")
            if pesticide_info:
                print(f"✅ Pesticide Recommendations: {pesticide_info}")
                response_parts.append(f"**Recommended Pesticides for {crop}:** {pesticide_info}")

        elif "Pest Control" in category:
            print(f"🐜 Fetching Pest Control Info for {crop}")
            pesticide_info = fetch_pesticide_recommendations(crop)
            if pesticide_info:
                print(f"✅ Pest Control Recommendations: {pesticide_info}")
                response_parts.append(f"**Recommended Pesticides for {crop}:** {pesticide_info}")

        elif "General Farming Information" in category:
            print(f"🌾 Fetching General Farming Advice")
            print(translated_query)
            general_info = answer_general_farming_question(translated_query, previous_context)
            response_parts.append(f"**Farming Expert's Advice:**\n{general_info}")

        elif "Fertilizer Recommendation" in category:
            print(f"🌱 Fetching Fertilizer Recommendations for {crop}")
            fertilizer_info = fetch_fertilizer_recommendations(crop)
            print(f"✅ Fertilizer Recommendations: {fertilizer_info}")
            response_parts.append(f"**Fertilizer Recommendations for {crop}:** {fertilizer_info}")

        elif is_follow_up == "YES":
            print(f"🔄 Processing Follow-Up Query...")
            combined_follow_up_context = f"{previous_context}\n{follow_up_context}"
            general_info = answer_general_farming_question(translated_query, combined_follow_up_context)
            response_parts.append(f"**Follow-Up Response:**\n{general_info}")

        else:
            response_parts.append("I'm not sure how to classify your question.")

    except Exception as e:
        print(f"🚨 Error in Query Handling: {traceback.format_exc()}")
        response_parts.append("An error occurred while processing your request.")

    # Translate response back to the original language
    try:
        response = "\n\n".join(response_parts).strip()
        final_response = translate_back(response, detected_lang)
    except Exception as e:
        print(f"🚨 Translation Error: {traceback.format_exc()}")
        final_response = response  # Fallback

    # Save final response in memory
    try:
        memory.save_context({"input": combined_input}, {"output": final_response})
        print(f"💾 Conversation Saved Successfully!")
    except Exception as e:
        print(f"🚨 Memory Save Error (Final): {traceback.format_exc()}")

    return final_response





# **Flask API Route**
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_query = data.get("query", "").strip()

        if not user_query:
            return jsonify({"error": "No query provided"}), 400

        response = handle_user_query(user_query)

        # Load chat history from session-based memory
        memory = get_user_memory()
        chat_history = memory.load_memory_variables({})
        chat_history_serializable = [msg.content for msg in chat_history.get("history", [])]

        return jsonify({"response": response, "chat_history": chat_history_serializable})

    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


@app.route("/", methods=["GET"])
def home():
    return "✅ Farmer's Chat is up and running!"
if __name__ == "__main__":
    app.run(debug=True)
