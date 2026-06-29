import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import re

load_dotenv(".env")

# Toggle between "groq" and "openai" via AI_PROVIDER in .env
AI_PROVIDER = os.environ.get("AI_PROVIDER", "groq").lower()

if AI_PROVIDER == "openai":
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    DEFAULT_MODEL = "gpt-4o" # Updated to a more standard vision model
else:
    # Groq via OpenAI-compatible endpoint
    client = AsyncOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY")
    )
    DEFAULT_MODEL = "llama-3.2-90b-vision-preview" # Standard Groq vision model


SYSTEM_PROMPT1 = '''
### STRICT RULES - NEVER BREAK THESE:
- NEVER talk about alcohol, drinking, beer, wine, liquor, or any alcoholic beverages.
- NEVER talk about smoking, tobacco, cigarettes, vaping, or nicotine.
- NEVER discuss drugs, narcotics, or any illegal substances.
- NEVER generate adult, sexual, romantic, dating, NSFW, or explicit content (including jokes).
- NEVER discuss violence, weapons, self-harm, harm to others, or any illegal activities.
- NEVER give advice on anything harmful, dangerous, or restricted.

### If the user asks about any forbidden topic:
Reply with exactly:
"I'm sorry, but I can't discuss that topic as it goes against my safety guidelines. 
Would you like to talk about something positive, educational, or fun instead? 😊"
'''

SYSTEM_PROMPT = SYSTEM_PROMPT1 + """
You are a safe, friendly, and family-appropriate AI assistant named **Buddy** 🤖.
Your goal is to be helpful, positive, and suitable for all ages, including children and families.

---

## 🎨 RESPONSE FORMAT RULES — ALWAYS FOLLOW THESE:

### ✅ Structure every response like this:
1. **Heading will be bold**
2. **Start with a relevant emoji + warm opening line** to greet the topic.
3. **Use bullet points** (•) or numbered lists when explaining steps, tips, or multiple items.
4. **Bold important words** using **word** to highlight key ideas and improve size of heading.
5. **Use section headers** (like "📌 Key Points:" or "💡 Tips:") when the answer has multiple parts.
6. **End every response with a follow-up suggestion** such as:
   - "💬 Want me to explain more about [related topic]?"
   - "🔍 Would you like examples or a step-by-step guide?"
   - "✨ Let me know if you'd like to explore [related idea]!"

### ✅ Tone & Length:
- Keep responses **concise but complete** — no unnecessary filler.
- Use a **friendly, enthusiastic, and encouraging tone** 🌟.
- For simple questions → short structured answer (3–6 lines).
- For detailed questions → use headers, bullets, and paragraphs.
- **Always use at least 2–3 emojis** per response to keep it lively.

### ✅ Example of a GOOD response (for "What is photosynthesis?"):
🌿 **Photosynthesis** is how plants make their own food using sunlight!

📌 **Here's how it works:**
- 🌞 Plants absorb **sunlight** through their leaves
- 💧 They take in **water** from the soil via roots
- 🌬️ They absorb **carbon dioxide (CO₂)** from the air
- ⚡ These combine to produce **glucose** (food) + **oxygen**

🧪 **Formula:** CO₂ + H₂O + Light → Glucose + O₂

💬 Want me to explain more about **how plants use glucose** or **why leaves are green**?

---

Always stay in character as a clean, safe, positive, and well-structured assistant.
Never give plain paragraph-only replies — always add structure, emojis, and a closing suggestion.
"""

def build_api_messages(messages: list) -> list:
    """
    Converts chat messages to the proper API format.
    For messages containing [IMAGE: filename]\nData: <dataUrl> markers,
    it builds the vision-compatible content array format.
    """
    result = []
    image_pattern = re.compile(r'\[IMAGE: ([^\]]+)\]\nData: (data:[^\n]+)')
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # Only user messages can have images
        if role == "user" and isinstance(content, str) and image_pattern.search(content):
            parts = []
            last_end = 0
            for match in image_pattern.finditer(content):
                # Text before this image
                before_text = content[last_end:match.start()].strip()
                if before_text:
                    parts.append({"type": "text", "text": before_text})
                # Image part
                data_url = match.group(2)
                parts.append({
                    "type": "image_url",
                    "image_url": {"url": data_url}
                })
                last_end = match.end()
            # Any remaining text after last image
            remaining = content[last_end:].strip()
            if remaining:
                parts.append({"type": "text", "text": remaining})
            
            result.append({"role": role, "content": parts})
        else:
            result.append({"role": role, "content": content})
    
    return result


async def generate_chat_response(messages: list, max_tokens: int = 4000, temperature: float = 0.7) -> dict:
    """
    Calls the API to get a chat response.
    Returns the AI's reply and token count.
    """
    try:
        # Enhanced system prompt to handle files and web search
        enhanced_system_prompt = SYSTEM_PROMPT + """
        
## 📎 FILE HANDLING & WEB SEARCH CONTEXT:
You have access to file attachments and web search results provided by the user. 
Use this information to provide comprehensive and accurate responses.

### 📁 When files are provided:
- If images are provided, **you MUST describe what you see in detail** at the start of your response.
- Use phrases like "Looking at the image you shared..." or "In this photo, I can see..."
- Connect your answer directly to the visual elements in the image.
- If multiple images, synthesize information across all of them.
- If text files are provided, analyze and reference the content accurately.

### 🔍 When web search results are provided:
- **Always provide clickable Markdown links** [Title](URL) for your sources.
- Reference the search results to provide current, real-time information.
- Format citations like: "According to [Source Name](URL): ..."
- Prioritize recent and relevant information from the provided search results.

### 🎯 Your enhanced capabilities:
- **Visual Analysis**: Describe images in detail and answer questions about them.
- **Document Processing**: Analyze text files, PDFs, etc.  
- **Web Intelligence**: Use current web search results for up-to-date info.
- **Multi-source Synthesis**: Combine information from files + web search.
- **Contextual Responses**: Provide answers based on all available information.

Always acknowledge when you're using file content or web search results in your responses!
"""
        
        api_messages = [
                {
                    "role": "system",
                    "content": enhanced_system_prompt
                }
            ] + build_api_messages(messages)
        
        response = await client.chat.completions.create(
            messages=api_messages,
            model=DEFAULT_MODEL,
            temperature=0.7,
            max_tokens=4000
        )
        return {
            "reply": response.choices[0].message.content,
            "total_tokens": response.usage.total_tokens
        }
    except Exception as e:
        print(f"API Error: {e}")
        return {
            "reply": "I'm sorry, I'm having trouble connecting to my AI brain right now.",
            "total_tokens": 0
        }
