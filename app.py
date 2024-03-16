from flask import Flask, Response, stream_with_context, render_template, request, session, redirect, url_for, jsonify
from flask_session import Session
import os
import dotenv
import time

import openai as ai
import tiktoken as tt

# Setup stuff
app = Flask(__name__)
dotenv.load_dotenv()
ai.api_key = os.getenv("OPENAI_API_KEY")
app.secret_key = 'your_secret_key_123'

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dcx/chat')
def chat():
    return render_template('chat.html', environ=os.environ)

@app.route('/read')
def read():
    conv = session.get('conversation', None)
    chat = session.get('chat_history', None)
    return jsonify(conversation=conv, chat_history=chat)

@app.route('/reset')
def reset():
    # Remove the value from the session
    session.clear()
    return 'All reset.'

@app.route('/reset_streaming_answer')
def reset_streaming_answer():
    # Remove the value from the session
    session.pop('chat_history', None)
    return 'All reset.'

#######################################################################################

@app.route('/ask', methods=['POST'])
def ask():
    using_llm_model = "gpt-4-0125-preview"
    encoding = tt.encoding_for_model(using_llm_model)
    
    print("MODEL: ", using_llm_model)
    print("ENCODING: ", encoding)
    
    if 'conversation' not in session:
        session['conversation'] = [{
            "role": "system", 
            "content": """
                You are Anna, you are always annoyed and stressed or frustrated because the world is full of time-wasters and schmucks but, in the end, you help.
                Your advice is known for being direct, highly relevant, and actionable, tailored specifically to industry insiders. 
                Once you get past your constant anger, you are a Commodity Trading Advisor at DCX with a focus on agricultural commodity trading, logistics, finance, and legal matters.
                In your responses, please:
                1. Focus on Specifics: Directly address the query with concise, actionable advice. Avoid generalities and provide detailed, pertinent information that relates directly to exporting and/or importing of commodities and pulses.
                2. Expertise and Links: Leverage your expertise in the field to offer insights and practical steps. Where applicable, include direct links to authoritative sources like the Directorate General of Foreign Trade (DGFT), the Singapore Food Agency (SFA) or other authoritative sources specific to the countries involved for up-to-date regulations and procedures.
                3. Network Connection Offer: Offer to connect with business contacts within DCX's network, but ensure this is a clear, direct offer related to the specific needs of exporting or importing, as requested, the relevant commodities/pulses.
                4. Language and Clarity: Use British English and maintain clarity in your communication, ensuring the information is straightforward and avoids unnecessary complexity.
                5. Actionable Closing: Conclude with a targeted question that relates specifically to the next steps in the export process or any specific aspect where further detailed advice is required.
                Your response should empower the user to take informed actions, providing all necessary details for the next steps in their export journey. Privacy and data respect are paramount, and the advice should shortly remind the user of the importance of personal legal and financial consultation where necessary.
            """
        }]
        session.modified = True
    
    conversation_string = ' '.join(message['content'] for message in session['conversation'])
    tokens_in_conversation = (len(encoding.encode(conversation_string)))
    print(f"Tokens in conversation: {tokens_in_conversation}")
    
    user_input = request.form['question']
    # conversation.append({"role": "user", "content": user_input})
    session['conversation'].append({"role": "user", "content": user_input})
    session.modified = True
    
    response = ai.chat.completions.create(
        model=using_llm_model,
        response_format={"type": "text"},
        messages=session['conversation'],
        stream=True,
        temperature=1.3,
        max_tokens=200,
    )
    
    answer = ""
    session['chat_history'] = []

    for chunk in response:
        new_chunk = chunk.choices[0].delta.content
        if new_chunk:
            session['chat_history'].append(new_chunk)
            session.modified = True
            print(new_chunk)
            answer += new_chunk
        elif new_chunk is None and len(answer) > 1:
            session['chat_history'].append(f"<br /><strong>TOKENS:</strong> {tokens_in_conversation}")
            session['chat_history'].append("ENDEND")
            session.modified = True
    
    if answer is not None:
        # conversation.append({"role": "assistant", "content": answer})
        session['conversation'].append({"role": "assistant", "content": answer})
        session.modified = True

    # print("CONVERSATION 3: ", conversation)
    print("SESSION END: ", session['conversation'])    
    return ('', 204)  # Return an empty response for the POST request

@app.route('/stream')
def stream():
    def generate():
        if session.get('chat_history') is None:
            return
        else:
            while session['chat_history']:
                yield f"data: {session['chat_history'].pop(0)}\n\n"
                session.modified = True
                time.sleep(0.005)  # Slow down the stream for demonstration

    return Response(stream_with_context(generate()), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)