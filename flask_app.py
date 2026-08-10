import os
import json
import tempfile
from flask import Flask, request, jsonify, Response, send_file, make_response
from flask_cors import CORS
import PyPDF2
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import ollama
import io
import re
from pathlib import Path
import pypandoc # Replaced markdown and xhtml2pdf with pypandoc
import email_manager
import chatbot_engine

app = Flask(__name__)
# Global CORS configuration
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Global Error Handler
@app.errorhandler(Exception)
def handle_global_error(e):
    response = jsonify({"error": f"Unhandled Server Error: {str(e)}"})
    response.status_code = 500
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# --- INITIALIZATION & PATHS ---
base_dir = Path(__file__).resolve().parent
db_path = base_dir / "Zomato_DB"
notices_path = base_dir / "downloaded_notices"
employee_summaries_path = base_dir / "employee_summaries"

print("\n" + "="*40)
print("🚀 ANTIGRAVITY SERVER INITIALIZING")
print("="*40)
print(f"Database Path: {db_path} (Exists: {db_path.exists()})")
print(f"Notices Path:  {notices_path} (Exists: {notices_path.exists()})")
print("="*40 + "\n")

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path=str(db_path))
embedding_function = SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-large-en-v1.5")
collection = chroma_client.get_or_create_collection(name="Zomato", embedding_function=embedding_function)

# --- API ENDPOINTS ---

@app.route('/api/analyze_upload', methods=['POST'])
def analyze_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        pdf_reader = PyPDF2.PdfReader(file)
        pdf_text = "".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])

        query_probe = pdf_text[:1000].replace('\n', ' ')
        query_text = f"Represent this sentence for searching relevant passages: {query_probe}"

        results = collection.query(query_texts=[query_text], n_results=4)

        context_chunks = []
        policies = []

        if results and 'documents' in results and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                context_chunks.append(doc)
                metadata = results['metadatas'][0][i] if 'metadatas' in results and results['metadatas'] else {}
                policy_name = metadata.get('source', f"Relevant Policy Fragment {i+1}")
                if policy_name not in policies:
                    policies.append(policy_name)
                    
        context_string = "\n\n---\n\n".join(context_chunks)

        return jsonify({
            "pdf_text": pdf_text,
            "context": context_string,
            "policies": policies if policies else ["Regulatory Compliance Guide"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/analyze_folder', methods=['GET'])
def analyze_folder():
    if not notices_path.exists():
        return jsonify({"error": f"Folder not found: {notices_path}"}), 404

    pdf_files = list(notices_path.glob("*.pdf"))
    results_list = []

    for file_path in pdf_files:
        try:
            filename = file_path.name
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                pdf_text = "".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
            
            query_probe = pdf_text[:1000].replace('\n', ' ')
            query_text = f"Represent this sentence for searching relevant passages: {query_probe}"

            db_results = collection.query(query_texts=[query_text], n_results=4)

            context_chunks = []
            policies = []

            if db_results and 'documents' in db_results and len(db_results['documents']) > 0:
                for i, doc in enumerate(db_results['documents'][0]):
                    context_chunks.append(doc)
                    metadata = db_results['metadatas'][0][i] if 'metadatas' in db_results and db_results['metadatas'] else {}
                    policy_name = metadata.get('source', f"Relevant Policy Fragment {i+1}")
                    if policy_name not in policies:
                        policies.append(policy_name)
                        
            context_string = "\n\n---\n\n".join(context_chunks)

            results_list.append({
                "filename": filename,
                "pdf_text": pdf_text,
                "context": context_string,
                "policies": policies if policies else ["Regulatory Compliance Guide"]
            })
        except Exception as e:
            print(f"Error processing {file_path.name}: {str(e)}")

    return jsonify({"files": results_list})


@app.route('/api/stream_audit', methods=['POST'])
def stream_audit():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    pdf_text = data.get('pdf_text', '')
    policy_context = data.get('policy_context', '')

    prompt = f"""
You are RegAI, an expert AI Corporate Compliance Auditor.
Analyze the following document against the retrieved corporate policy context. Provide a detailed compliance memo, including identified gaps, recommendations, and overall assessment.

[RETRIEVED POLICIES CONTEXT]
{policy_context}

[DOCUMENT TO AUDIT]
{pdf_text[:4000]}
"""
    def generate():
        try:
            stream = ollama.chat(
                model='deepseek-r1',
                messages=[{'role': 'user', 'content': prompt}],
                stream=True,
            )
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
        except Exception as e:
            yield f"\n\n[Audit Generation Failed: {str(e)}]"

    return Response(generate(), mimetype='text/event-stream')


# --- EMPLOYEE DASHBOARD ENDPOINTS ---

@app.route('/api/employee/updates', methods=['GET'])
def get_employee_updates():
    try:
        if not employee_summaries_path.exists():
            return jsonify([])
            
        updates = []
        for json_file in employee_summaries_path.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                updates.append({
                    "filename": data.get("filename", json_file.name.replace(".json", ".pdf")),
                    "summary": data.get("summary", ""),
                    "impact": data.get("impact", ""),
                    "benefits": data.get("benefits", "")
                })
        return jsonify(updates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/employee/flash_alerts', methods=['GET'])
def get_flash_alerts():
    try:
        if not employee_summaries_path.exists():
            return jsonify({"alerts": []})
            
        all_alerts = []
        for json_file in employee_summaries_path.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                alerts = data.get("flash_alerts", [])
                all_alerts.extend(alerts)
        return jsonify({"alerts": all_alerts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notices/<filename>', methods=['GET', 'OPTIONS'])
def get_notice_pdf(filename):
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        return resp
        
    try:
        # Prevent directory traversal by only taking the basename
        safe_filename = os.path.basename(filename)
        file_path = notices_path / safe_filename
        
        if not file_path.exists() or not str(file_path).endswith('.pdf'):
            resp = jsonify({"error": "PDF not found or invalid format"})
            resp.status_code = 404
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp
            
        resp = make_response(send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=False
        ))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    except Exception as e:
        resp = jsonify({"error": str(e)})
        resp.status_code = 500
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

# --- COMMUNICATION CENTER ENDPOINTS ---

@app.route('/api/recipients', methods=['GET', 'POST', 'PUT', 'OPTIONS'])
def handle_recipients():
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
        return resp
        
    if request.method == 'GET':
        recipients = email_manager.load_recipients()
        resp = jsonify(recipients)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
        
    if request.method == 'POST':
        data = request.json
        email = data.get('email')
        if not email:
            resp = jsonify({"error": "Email is required"})
            resp.status_code = 400
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp
            
        success = email_manager.add_recipient(email)
        if success:
            resp = jsonify({"message": "Recipient added"})
        else:
            resp = jsonify({"message": "Recipient already exists"})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
        
    if request.method == 'PUT':
        data = request.json
        old_email = data.get('old_email')
        new_email = data.get('new_email')
        
        if not old_email or not new_email:
            resp = jsonify({"error": "Both old_email and new_email are required"})
            resp.status_code = 400
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp
            
        success, message = email_manager.update_recipient(old_email, new_email)
        if success:
            resp = jsonify({"message": message})
        else:
            resp = jsonify({"error": message})
            resp.status_code = 400
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

@app.route('/api/recipients/<email>', methods=['DELETE', 'OPTIONS'])
def delete_recipient(email):
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'DELETE, OPTIONS'
        return resp
        
    success = email_manager.remove_recipient(email)
    if success:
        resp = jsonify({"message": "Recipient removed"})
    else:
        resp = jsonify({"message": "Recipient not found"})
        resp.status_code = 404
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/api/dispatch_audit', methods=['POST', 'OPTIONS'])
def dispatch_audit():
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return resp
        
    try:
        data = request.json
        if not data or 'filename' not in data or 'content' not in data:
            resp = jsonify({"error": "Missing filename or content payload."})
            resp.status_code = 400
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp

        filename = data['filename']
        content = data['content']
        safe_filename = re.sub(r'[^a-zA-Z0-9.\-_]', '_', filename)
        
        clean_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        markdown_content = f"# AntiGravity Compliance Audit\n\n**Source Notice:** {filename}\n\n---\n\n{clean_content}"

        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            temp_path = tmp.name

        try:
            pypandoc.convert_text(
                source=markdown_content, 
                format='md', 
                to='docx', 
                extra_args=['--reference-doc=reference.docx'],
                outputfile=temp_path
            )
            with open(temp_path, 'rb') as f:
                docx_bytes = f.read()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        attachment_name = f"{safe_filename.replace('.pdf', '')}_RegAI_Memo.docx"
        count = email_manager.send_compliance_email(docx_bytes, attachment_name)
        
        resp = jsonify({"message": f"Audit dispatched to {count} recipients."})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

    except Exception as e:
        print(f"Dispatch Error: {e}")
        resp = jsonify({"error": f"Dispatch Error: {str(e)}"})
        resp.status_code = 500
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

# --- CHATBOT ENGINE ---

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def handle_chat():
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return resp
        
    try:
        data = request.json
        user_message = data.get('message')
        if not user_message:
            resp = jsonify({"error": "Message is required"})
            resp.status_code = 400
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp
            
        ai_response = chatbot_engine.get_chat_response(user_message)
        resp = jsonify({"response": ai_response})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    except Exception as e:
        print(f"Chatbot Error: {e}")
        resp = jsonify({"error": "Internal Chatbot Error"})
        resp.status_code = 500
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

# --- DOCUMENT GENERATION ENGINE (Markdown -> DOCX) ---

@app.route('/api/generate_docx', methods=['POST', 'OPTIONS'])
def generate_document():
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return resp

    try:
        data = request.json
        if not data:
            resp = jsonify({"error": "No JSON payload provided"})
            resp.status_code = 400
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp

        filename = data.get('filename', 'Audit_Memo')
        safe_filename = re.sub(r'[^a-zA-Z0-9.\-_]', '_', filename)
        content = data.get('content', '')

        # 1. Clean the AI reasoning blocks
        clean_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        
        # 2. Prepend a header directly into the markdown content
        markdown_content = f"# RegAI Compliance Audit\n\n**Source Notice:** {filename}\n\n---\n\n{clean_content}"

        # 3. Create a temporary file to save the docx output
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            temp_path = tmp.name

        try:
            # 4. Generate the DOCX file directly from the markdown string
            pypandoc.convert_text(
                source=markdown_content, 
                format='md', 
                to='docx', 
                extra_args=['--reference-doc=reference.docx'], # Applies your Calibri styles
                outputfile=temp_path
            )

            # 5. Read the bytes back into memory so we can safely delete the temp file
            with open(temp_path, 'rb') as f:
                docx_bytes = f.read()
        finally:
            # 6. Clean up the temporary file immediately
            if os.path.exists(temp_path):
                os.remove(temp_path)

        # 7. Send back to frontend as a DOCX attachment
        resp = make_response(send_file(
            io.BytesIO(docx_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=f"{safe_filename.replace('.pdf', '')}_RegAI_Memo.docx"
        ))
        
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

    except Exception as e:
        print(f"DOCX Generation Error: {e}")
        resp = jsonify({"error": f"DOCX Generation Error: {str(e)}"})
        resp.status_code = 500
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)