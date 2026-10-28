import ollama
import datetime
import re
import logging
from config import LLM_MODEL

logger = logging.getLogger(__name__)

def handle_simple_interaction(question):
    """Return a short response if the user is greeting or thanking, otherwise None."""
    q = question.lower().strip()
    q_clean = re.sub(r'[^\w\s]', '', q)

    greeting_words = ["hi", "hello", "hey", "greetings"]
    greeting_phrases = ["good morning", "good afternoon", "good evening"]

    words = q_clean.split()
    if len(words) <= 3:
        if any(g in words for g in greeting_words) or any(p in q_clean for p in greeting_phrases):
            hour = datetime.datetime.now().hour
            if 5 <= hour < 12:
                time_greet = "Good morning"
            elif 12 <= hour < 17:
                time_greet = "Good afternoon"
            elif 17 <= hour < 21:
                time_greet = "Good evening"
            else:
                time_greet = "Hello"
            return f"{time_greet}! How can I assist you with your studies today?"

    thanks_phrases = ["thank you", "thanks", "thank u", "thx", "thankyou"]
    if any(p in q_clean for p in thanks_phrases):
        return "You're very welcome! I'm always here to help you learn. 😊"

    return None

def detect_simplify_request(question):
    """Check if question asks for explanation in simple terms."""
    q = question.lower()
    patterns = [
        r"explain like (i'm|i am) (\d+)",
        r"for (a|an?) (\d+)[-\s]year[-\s]old",
        r"in simple terms",
        r"for beginners?",
        r"easy explanation",
        r"child friendly",
        r"like i'm (\d+)",
    ]
    return any(re.search(p, q) for p in patterns)

def ask_llm_with_context_and_history(question, context_chunks, history):
    """Answer based on context, with length and format adapted to user's request."""
    if not context_chunks:
        return "Sorry, the asked content is not available in the course notes. Please ask a course‑oriented question."

    # Detect length preferences
    short_keywords = ["short answer", "briefly", "in short", "concise", "tl;dr"]
    is_short = any(keyword in question.lower() for keyword in short_keywords)

    # Detect pointwise requests
    point_keywords = ["in points", "list", "enumerate", "bullet points", "pointwise", "list down"]
    is_pointwise = any(keyword in question.lower() for keyword in point_keywords)

    # Build instruction
    if is_short and is_pointwise:
        length_instruction = "Provide a very concise answer in bullet points (use '-' for each point), no more than 3-4 points, using only the notes."
    elif is_short:
        length_instruction = "Provide a very concise answer, no more than 2-3 sentences, using only the notes."
    elif is_pointwise:
        length_instruction = "Provide a clear answer in bullet points (use '-' for each point), using only the notes."
    else:
        length_instruction = "Provide a clear and concise answer, around 3-5 sentences, using only the notes."

    context = "\n\n".join(context_chunks)

    # Format conversation history
    history_text = ""
    if history:
        history_lines = []
        for msg in history:
            role = "Student" if msg["role"] == "user" else "Assistant"
            history_lines.append(f"{role}: {msg['content']}")
        history_text = "Previous conversation:\n" + "\n".join(history_lines) + "\n\n"

    prompt = f"""You are a helpful teaching assistant. Answer the student's question based ONLY on the provided course notes. If the notes do not contain the answer, say that the topic is not covered. Do not use outside knowledge.

{length_instruction}

{history_text}Notes:
{context}

Question: {question}

Answer:"""
    logger.info(f"Prompt length: {len(prompt)} characters, history included: {len(history)>0}")
    response = ollama.chat(model=LLM_MODEL, messages=[{'role': 'user', 'content': prompt}])
    logger.info(f"LLM response received, length: {len(response['message']['content'])} chars")
    return response['message']['content']

def ask_llm_deeper(question):
    """Generate a detailed, beginner‑friendly explanation using the model's own knowledge."""
    prompt = f"""Explain the following topic in a beginner‑friendly, detailed way, using your own knowledge:
{question}"""
    logger.info(f"Deep prompt length: {len(prompt)} chars")
    response = ollama.chat(model=LLM_MODEL, messages=[{'role': 'user', 'content': prompt}])
    logger.info(f"Deep response length: {len(response['message']['content'])} chars")
    return response['message']['content']

def ask_llm_follow_up(question, last_assistant_response):
    """Answer a follow‑up question (like 'tell me more') based on the last assistant response."""
    prompt = f"""The user asked a follow‑up question based on the previous answer. Use the previous answer to respond appropriately.

Previous answer:
{last_assistant_response}

Follow‑up question: {question}

Answer:"""
    logger.info(f"Follow‑up prompt length: {len(prompt)} chars")
    response = ollama.chat(model=LLM_MODEL, messages=[{'role': 'user', 'content': prompt}])
    logger.info(f"Follow‑up response length: {len(response['message']['content'])} chars")
    return response['message']['content']

def ask_llm_summarize(text):
    """Summarize the given text into one paragraph."""
    prompt = f"""Summarize the following text into a single concise paragraph:

{text}

Summary:"""
    logger.info(f"Summarize prompt length: {len(prompt)} chars")
    response = ollama.chat(model=LLM_MODEL, messages=[{'role': 'user', 'content': prompt}])
    logger.info(f"Summarize response length: {len(response['message']['content'])} chars")
    return response['message']['content']

def ask_llm_simplify(question, context=None):
    """Explain a topic in very simple terms (like for a child)."""
    if context:
        prompt = f"""Explain the following concept in extremely simple terms, as if to a 5‑year‑old child, using the provided context if helpful:

Context: {context}

Concept: {question}

Simple explanation:"""
    else:
        prompt = f"""Explain the following concept in extremely simple terms, as if to a 5‑year‑old child:

{question}

Simple explanation:"""
    logger.info(f"Simplify prompt length: {len(prompt)} chars")
    response = ollama.chat(model=LLM_MODEL, messages=[{'role': 'user', 'content': prompt}])
    logger.info(f"Simplify response length: {len(response['message']['content'])} chars")
    return response['message']['content']

def is_follow_up_question(question, history):
    """Ask LLM to determine if the question is a follow-up to the last assistant response."""
    if not history:
        return False
    # Get the last assistant message
    last_assistant = None
    for msg in reversed(history):
        if msg["role"] == "assistant":
            last_assistant = msg["content"]
            break
    if not last_assistant:
        return False

    prompt = f"""You are a conversation analyzer. Determine if the new user question is a follow-up to the previous assistant response, meaning it asks for more detail, clarification, summary, or is related to the same topic. Answer only with 'yes' or 'no'.

Previous assistant response: {last_assistant}

New user question: {question}

Is this a follow-up question? Answer yes or no:"""
    logger.info("Checking if question is a follow-up")
    response = ollama.chat(model=LLM_MODEL, messages=[{'role': 'user', 'content': prompt}])
    answer = response['message']['content'].strip().lower()
    logger.info(f"Follow-up classification: {answer}")
    return answer.startswith('yes')