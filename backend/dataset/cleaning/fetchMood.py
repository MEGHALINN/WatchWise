from google import genai
import pandas as pd
import json
import time
import signal
import sys
import os
from dotenv import load_dotenv

load_dotenv()

api_keys = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5")
]
api_keys = [k for k in api_keys if k] # Filter out None
used_keys = []  # Stores exhausted API keys to retry later

client = None
model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Function to configure API key
def switch_api_key():
    global current_api_key, client

    if api_keys:
        current_api_key = api_keys.pop(0)  # Use the first key
        client = genai.Client(api_key=current_api_key)
        print(f"🔄 Switched to API key: {current_api_key[:10]}******")
    elif used_keys:
        print("🔄 Retrying used API keys...")
        api_keys.extend(used_keys)  # Move used keys back to available list
        used_keys.clear()
        switch_api_key()
    else:
        print("❌ No API keys left! Exiting...")
        save_progress()
        exit()

switch_api_key()

file_path = "netflix_mood_recommender_test_corrected.csv"
df = pd.read_csv(file_path)

# Function to save progress
def save_progress():
    df.to_csv("netflix_mood_with_predictions.csv", index=False)
    print("💾 Progress saved to 'netflix_mood_with_predictions.csv'")

# Handle keyboard interrupt
def handle_interrupt(signal, frame):
    print("\n🚨 Keyboard Interrupt detected! Saving progress...")
    save_progress()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_interrupt)

# Function to determine mood from multiple descriptions at once
def get_moods_from_descriptions(descriptions):
    prompt = f"""
    Analyze the given movie descriptions and determine 2 of the most appropriate mood for each one from the following list: 
    [relaxed, curious, tense, excited, lonely, scared, annoyed, anger, disgust, fear, joy, sadness, romantic, surprise].
    
    Your response **must** be a valid JSON object with movie indices as keys and their corresponding moods as values.
    
    Example format:
    {{
        "0": "joy, romantic",
        "1": "romantic, surprise",
        "2": "fear, disgust"
    }}
    
    Here are the descriptions:
    {json.dumps(descriptions, indent=2)}
    """
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )

        # Print raw response for debugging
        print("Raw API Response:", response.text)

        # Extract response text safely
        if hasattr(response, "text") and response.text.strip():
            json_text = response.text.strip()

            # Ensure we only extract the JSON part
            json_start = json_text.find("{")
            json_end = json_text.rfind("}")
            if json_start != -1 and json_end != -1:
                json_text = json_text[json_start : json_end + 1]

            return json.loads(json_text)  # Convert to dictionary
    except Exception as e:
        error_message = str(e).lower()
        print("⚠️ API Error:", e)

        # Check if quota limit is reached
        if "quota" in error_message or "rate limit" in error_message:
            print(f"⚠️ API Key {current_api_key[:10]}****** exhausted. Trying another key...")

            used_keys.append(current_api_key)  # Save exhausted key
            switch_api_key()  # Switch to next key
            return get_moods_from_descriptions(descriptions)  # Retry with new key

        return {}  # Return empty dict if another error occurs

# Batch process descriptions
batch_size = 10
moods = []

try:
    for i in range(0, len(df), batch_size):
        batch = df["description"][i:i+batch_size].to_dict()
        mood_dict = get_moods_from_descriptions(batch)

        batch_moods = [mood_dict.get(str(idx), "unknown") for idx in batch.keys()]
        moods.extend(batch_moods)

        print(f"✅ Processed batch {i//batch_size + 1}/{(len(df) // batch_size) + 1}")

        # Save progress after each batch
        df.loc[i:i+batch_size-1, "mood"] = batch_moods
        save_progress()

        time.sleep(1)
except Exception as e:
    print(f"🚨 An error occurred: {e}")
    save_progress()
    sys.exit(1)

save_progress()
print("🎉 Mood analysis completed and saved to 'netflix_mood_with_predictions.csv'")