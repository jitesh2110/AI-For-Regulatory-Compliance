# 🌌  RegAI Compliance Suite

> **Empowering Corporate Compliance through Autonomous AI & Advanced RAG Pipelines**

**AntiGravity** is an advanced, AI-driven corporate compliance platform that automates the ingestion, analysis, and dissemination of regulatory changes. By bridging the gap between external regulatory notices (SEBI, RBI) and internal corporate policies, AntiGravity provides actionable intelligence, mitigating compliance risks through a state-of-the-art Retrieval-Augmented Generation (RAG) system.

---

## 🏗️ Detailed Architecture

AntiGravity operates on a highly decoupled, multi-stage pipeline designed for secure, localized data processing.

1. **Ingestion Layer:** Regulatory notices are scraped and downloaded as PDFs directly into the local `downloaded_notices` directory.
2. **Vectorization & Storage:** Corporate policies are embedded using `BAAI/bge-large-en-v1.5` and stored in a persistent **ChromaDB** instance (`Zomato_DB`), allowing for high-speed semantic similarity searches.
3. **Inference Engine (RAG):** When a new regulatory notice is detected, the system extracts the text and cross-references it against the ChromaDB policy store. The gathered context is fed into a locally hosted **Ollama (DeepSeek-R1)** model, which reasons about corporate impact.
4. **Dissemination:** The resulting insights are securely output as structured JSON into the `employee_summaries` directory for the Employee Portal, or streamed back to the Manager Command Center as detailed Markdown audits.

---

## 🚀 Feature Breakdown

AntiGravity is built with a dual-interface architecture to serve both compliance officers and standard employees securely.

### 🛡️ Manager Command Center
The core operational hub for Compliance Officers. Features a 'Cyber' dark theme for focused, data-heavy analysis.
* **Batch Processing:** Autonomously scan `downloaded_notices` and run the multi-probe vector search to generate comprehensive impact memos.
* **Streaming Reasoning:** Watch the DeepSeek-R1 model "think" in real-time as it breaks down complex legal jargon into actionable corporate policy updates.
* **Communication Center:** Manage employee distribution lists (`recipients.json`) and utilize the robust SMTP dispatcher to securely email generated **DOCX** compliance memos to the entire organization in one click.
* **Policy Concierge Chatbot:** A fully interactive RAG chatbot allowing managers to query internal policies in plain English.

### 👥 Employee Compliance Portal
A highly accessible, read-only interface for standard staff.
* **Simplified Intelligence:** Views plain-English translations of complex regulatory notices, stripping away legal jargon.
* **Secure PDF Viewing:** Employees can safely view the original regulatory PDFs via a secure file-serving bridge that prevents directory traversal.

---

## 💻 Tech Stack

### Backend
* **Python / Flask**: High-performance RESTful API.
* **ChromaDB**: Local Vector Database for persistent policy storage.
* **Ollama (DeepSeek-R1)**: Localized LLM inference engine for privacy-first AI generation.
* **Sentence Transformers**: `BAAI/bge-large-en-v1.5` for state-of-the-art embedding generation.
* **Document Engines**: `pypandoc` (DOCX formatting via reference templates) and `xhtml2pdf` (PDF generation).

### Frontend
* **React.js**: Fast, component-based UI architecture.
* **Tailwind CSS**: Rapid, utility-first styling utilizing a custom 'Cyber' design system (glassmorphism, neon accents).
* **Lucide-React**: Modern, crisp iconography.

---

## ⚙️ Step-by-Step Setup

Follow these instructions to deploy AntiGravity locally.

### 1. Prerequisites
Ensure you have Python 3.10+, Node.js (v18+), and Ollama installed on your system.

### 2. Initialize the AI Engine (Ollama)
Open your terminal and pull the required DeepSeek model:
```bash
ollama pull deepseek-r1
```

### 3. Backend Setup
Navigate to the project root and install the necessary Python dependencies:
```bash
pip install flask flask-cors chromadb sentence-transformers ollama pypandoc xhtml2pdf PyPDF2
```
Start the Flask Server:
```bash
python flask_app.py
```

### 4. Frontend Setup
Open a new terminal window, navigate to the frontend directory, and start the Vite development server:
```bash
cd frontend
npm install
npm run dev
```

---

## 🔌 API Overview

AntiGravity exposes a modular REST API to interface between the React frontend and the Python intelligence engines.

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/stream_audit` | `POST` | Streams the real-time reasoning and final output from the Ollama RAG pipeline for a specific document. |
| `/api/generate_docx` | `POST` | Converts the generated Markdown audit memo into a professionally styled DOCX file using `pypandoc`. |
| `/api/employee/updates`| `GET` | Fetches the pre-compiled, simplified JSON summaries for the Employee Portal. |
| `/api/notices/<filename>` | `GET` | Securely serves the original raw PDF notices to the browser. |
| `/api/recipients` | `GET/POST/PUT/DELETE`| Full CRUD interface for managing the employee email distribution list. |
| `/api/chat` | `POST` | Handles queries for the Policy Concierge chatbot, executing RAG against ChromaDB. |
| `/api/dispatch_audit` | `POST` | Generates a DOCX and triggers the SMTP email distribution engine. |




