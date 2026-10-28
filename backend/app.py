from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from collections import defaultdict
import time
import logging
from pdf_loader import load_all_pdfs
from vector_store import index_pdfs, get_relevant_chunks_with_sources
from llm_interface import (
    handle_simple_interaction,
    ask_llm_with_context_and_history,
    ask_llm_deeper,
    ask_llm_follow_up,
    ask_llm_summarize,
    ask_llm_simplify,
    is_follow_up_question,
    detect_simplify_request
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__,
            template_folder='../frontend',
            static_folder='../frontend/static')
CORS(app)

# Store conversation history (max 5 exchanges per session)
conversations = defaultdict(list)
MAX_HISTORY = 5

# Store last answer and sources per session (for follow-ups)
last_answer = {}
last_sources = {}

# ========== SERVE FRONTEND ==========
@app.route('/')
def home():
    logger.info("Serving frontend index.html")
    return render_template('index.html')

# ========== CHAT API ==========
@app.route('/chat', methods=['POST'])
def chat():
    start_total = time.time()
    data = request.json
    question = data.get('question', '').strip()
    deeper = data.get('deeper', False)
    session_id = data.get('sessionId', 'default')

    logger.info(f"Received request - session: {session_id}, deeper: {deeper}, question: '{question}'")

    if not question:
        logger.warning("Empty question received")
        return jsonify({"answer": "Please ask a question."})

    # Handle greetings and thanks immediately
    simple_start = time.time()
    simple_response = handle_simple_interaction(question)
    if simple_response:
        logger.info(f"Simple interaction handled in {time.time()-simple_start:.2f}s - response: '{simple_response}'")
        logger.info(f"Total request time: {time.time()-start_total:.2f}s")
        return jsonify({
            "answer": simple_response,
            "is_substantive": False
        })

    # Check if the question itself asks for simplified explanation
    if detect_simplify_request(question):
        logger.info("Detected simplify request")
        simplify_start = time.time()
        answer = ask_llm_simplify(question)
        logger.info(f"Simplify completed in {time.time()-simplify_start:.2f}s")
        # Store last answer for this session (no sources)
        last_answer[session_id] = answer
        last_sources[session_id] = []
        # Update history
        conversations[session_id].append({"role": "user", "content": question})
        conversations[session_id].append({"role": "assistant", "content": answer})
        if len(conversations[session_id]) > MAX_HISTORY * 2:
            conversations[session_id] = conversations[session_id][-MAX_HISTORY * 2:]
        logger.info(f"Total request time: {time.time()-start_total:.2f}s")
        return jsonify({
            "answer": answer,
            "is_substantive": True,
            "sources": []
        })

    if deeper:
        logger.info("Processing deep explanation request")
        deep_start = time.time()
        answer = ask_llm_deeper(question)
        logger.info(f"Deep explanation completed in {time.time()-deep_start:.2f}s")
        # Store last answer
        last_answer[session_id] = answer
        last_sources[session_id] = []
        # Update history
        conversations[session_id].append({"role": "user", "content": question})
        conversations[session_id].append({"role": "assistant", "content": answer})
        if len(conversations[session_id]) > MAX_HISTORY * 2:
            conversations[session_id] = conversations[session_id][-MAX_HISTORY * 2:]
        logger.info(f"Total request time: {time.time()-start_total:.2f}s")
        return jsonify({
            "answer": answer,
            "is_substantive": True,
            "sources": []
        })

    # Normal flow: retrieve chunks and answer with context + history
    retrieval_start = time.time()
    logger.info("Starting chunk retrieval")
    chunks, sources = get_relevant_chunks_with_sources(question)  # new function
    logger.info(f"Retrieved {len(chunks)} chunks in {time.time()-retrieval_start:.2f}s")
    if chunks:
        logger.info(f"First chunk preview: {chunks[0][:100]}...")
    else:
        logger.info("No relevant chunks found")
        # Check if it might be a follow‑up question
        history = conversations.get(session_id, [])
        if history and len(history) >= 2:
            meta_keywords = ["short", "brief", "summarize", "summary", "explain", "more", "detail", "in short", "tell me more"]
            if any(k in question.lower() for k in meta_keywords):
                if is_follow_up_question(question, history):
                    logger.info("Confirmed as follow‑up question, using last assistant response as context")
                    last = last_answer.get(session_id)
                    if last:
                        llm_start = time.time()
                        answer = ask_llm_follow_up(question, last)
                        logger.info(f"Follow‑up LLM call completed in {time.time()-llm_start:.2f}s")
                        # Store last answer (the new one)
                        last_answer[session_id] = answer
                        last_sources[session_id] = []
                        # Update history
                        conversations[session_id].append({"role": "user", "content": question})
                        conversations[session_id].append({"role": "assistant", "content": answer})
                        if len(conversations[session_id]) > MAX_HISTORY * 2:
                            conversations[session_id] = conversations[session_id][-MAX_HISTORY * 2:]
                        logger.info(f"Total request time: {time.time()-start_total:.2f}s")
                        return jsonify({
                            "answer": answer,
                            "is_substantive": True,
                            "sources": []
                        })

        # No chunks and not a relevant follow‑up → not available
        answer = "Sorry, the asked content is not available in the course notes. Please ask a course‑oriented question."
        last_answer[session_id] = answer
        last_sources[session_id] = []
        conversations[session_id].append({"role": "user", "content": question})
        conversations[session_id].append({"role": "assistant", "content": answer})
        if len(conversations[session_id]) > MAX_HISTORY * 2:
            conversations[session_id] = conversations[session_id][-MAX_HISTORY * 2:]
        logger.info(f"Total request time: {time.time()-start_total:.2f}s")
        return jsonify({
            "answer": answer,
            "is_substantive": False,
            "sources": []
        })

    # Get conversation history
    history = conversations.get(session_id, [])
    logger.info(f"Conversation history for session {session_id}: {len(history)} messages")

    llm_start = time.time()
    answer = ask_llm_with_context_and_history(question, chunks, history)
    logger.info(f"LLM call completed in {time.time()-llm_start:.2f}s")

    # Store last answer and sources
    last_answer[session_id] = answer
    last_sources[session_id] = sources

    # Update history
    conversations[session_id].append({"role": "user", "content": question})
    conversations[session_id].append({"role": "assistant", "content": answer})
    if len(conversations[session_id]) > MAX_HISTORY * 2:
        conversations[session_id] = conversations[session_id][-MAX_HISTORY * 2:]

    logger.info(f"Total request time: {time.time()-start_total:.2f}s")
    return jsonify({
        "answer": answer,
        "is_substantive": True,
        "sources": sources
    })

# ========== FOLLOW-UP ACTIONS ==========

@app.route('/source', methods=['POST'])
def source():
    data = request.json
    session_id = data.get('sessionId')
    sources = last_sources.get(session_id, [])
    if sources:
        source_text = "Sources:\n" + "\n".join(f"📄 {s}" for s in set(sources))
    else:
        source_text = "No source information available for this answer."
    return jsonify({"answer": source_text})

@app.route('/tellmore', methods=['POST'])
def tellmore():
    data = request.json
    session_id = data.get('sessionId')
    question = data.get('question', '')
    last = last_answer.get(session_id)
    if not last:
        return jsonify({"answer": "No previous answer to elaborate on."})
    answer = ask_llm_follow_up("Tell me more about this.", last)
    # Store as new last answer
    last_answer[session_id] = answer
    last_sources[session_id] = []
    # Update history
    conversations[session_id].append({"role": "user", "content": "Tell me more"})
    conversations[session_id].append({"role": "assistant", "content": answer})
    return jsonify({"answer": answer})

@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.json
    session_id = data.get('sessionId')
    last = last_answer.get(session_id)
    if not last:
        return jsonify({"answer": "No previous answer to summarize."})
    answer = ask_llm_summarize(last)
    # Store as new last answer (optional)
    last_answer[session_id] = answer
    last_sources[session_id] = []
    conversations[session_id].append({"role": "user", "content": "Summarize"})
    conversations[session_id].append({"role": "assistant", "content": answer})
    return jsonify({"answer": answer})

@app.route('/simplify', methods=['POST'])
def simplify():
    data = request.json
    session_id = data.get('sessionId')
    question = data.get('question', '')
    last = last_answer.get(session_id)
    if last:
        answer = ask_llm_simplify(question, context=last)
    else:
        answer = ask_llm_simplify(question)
    last_answer[session_id] = answer
    last_sources[session_id] = []
    conversations[session_id].append({"role": "user", "content": "Explain like I'm 5"})
    conversations[session_id].append({"role": "assistant", "content": answer})
    return jsonify({"answer": answer})

# ========== INDEXING (separate script) ==========
if __name__ == '__main__':
    logger.info("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=True)