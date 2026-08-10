import os
import re
import glob
import ollama
import chromadb
from PyPDF2 import PdfReader
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter

DOWNLOADED_DIR = "./downloaded_notices"
MEMO_DIR = "./compliance_memos"
DB_PATH = "./Zomato_DB"
COLLECTION_NAME = "Zomato"
OLLAMA_MODEL = "deepseek-r1"

DISTANCE_THRESHOLD = 1.3 

os.makedirs(MEMO_DIR, exist_ok=True)

# Use a splitter for the notice to intelligently bypass headers/Hindi text
notice_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ". ", " "]
)

def extract_pdf_text(filepath):
    """Extract and clean text, optimized for local RAM limits."""
    try:
        reader = PdfReader(filepath)
        extracted_text = ""
        
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + " "
                
        # Smart line cleaning
        clean_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', extracted_text)
        clean_text = re.sub(r' {2,}', ' ', clean_text).strip()
        
        MAX_CHARS = 15000 
        if len(clean_text) > MAX_CHARS:
            print(f"Warning: PDF is very large. Truncating to first {MAX_CHARS} characters to save RAM.")
            return clean_text[:MAX_CHARS]
            
        return clean_text
    except Exception as e:
        print(f"Failed to extract text from {filepath}: {e}")
        return None

def retrieve_zomato_policies(query_text):
    """Search ChromaDB using smart chunks and the required BGE-Large prefix."""
    try:
        chroma_client = chromadb.PersistentClient(path=DB_PATH)
        emb_fn = SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-large-en-v1.5")
        collection = chroma_client.get_collection(name=COLLECTION_NAME, embedding_function=emb_fn)
        
        # 1. Smartly split the notice into chunks to bypass headers and Hindi text
        notice_chunks = notice_splitter.split_text(query_text)
        
        # Take up to the first 4 viable chunks
        raw_probes = notice_chunks[:4] if notice_chunks else [query_text]
        
        # 2. Add the REQUIRED BGE-Large prefix to boost semantic accuracy
        bge_prefix = "Represent this sentence for searching relevant passages: "
        probes = [bge_prefix + probe for probe in raw_probes]
            
        results = collection.query(
            query_texts=probes,
            n_results=3, 
            include=['documents', 'metadatas', 'distances']
        )
        
        unique_contexts = set()
        context_str = ""
        absolute_lowest_distance = float('inf')
        policy_names = set()
        
        if results and 'documents' in results:
            for probe_idx, probe_distances in enumerate(results['distances']):
                for chunk_idx, distance in enumerate(probe_distances):
                    distance_val = float(distance)
                    
                    if distance_val < absolute_lowest_distance:
                        absolute_lowest_distance = distance_val
                        
                    doc_text = results['documents'][probe_idx][chunk_idx]
                    clean_doc = re.sub(r'\s+', ' ', doc_text).strip()
                    
                    meta = results['metadatas'][probe_idx][chunk_idx]
                    source_name = meta.get("source", "Unknown Policy")
                    
                    if clean_doc not in unique_contexts:
                        unique_contexts.add(clean_doc)
                        policy_names.add(source_name)
                        context_str += f"--- From Policy: {source_name} ---\n{clean_doc}\n\n"
        
        print("\n[DEBUG] Top Retrieved Policies for AI Review:")
        for name in policy_names:
            print(f" - {name}")
        print()
        
        final_distance = absolute_lowest_distance if absolute_lowest_distance != float('inf') else 0.0
        return final_distance, context_str.strip()
        
    except Exception as e:
        print(f"Error querying ChromaDB: {e}")
        return None, ""

def generate_compliance_memo(pdf_text, policy_context):
    """Orchestrate Ollama to analyze changes and stream a strict memo."""
    
    user_prompt = f"""You are Verifin, an Expert Corporate Compliance Auditor for Eternal Limited (formerly Zomato Limited).

<GOVERNMENT_NOTICE>
{pdf_text}
</GOVERNMENT_NOTICE>

<COMPANY_POLICIES>
{policy_context}
</COMPANY_POLICIES>

CRITICAL AUDIT INSTRUCTIONS:
1. Read the <GOVERNMENT_NOTICE> and compare it to the <COMPANY_POLICIES>. 
2. MAPPING CHEAT SHEET: Government notices use different words than internal policies. You MUST use these logical bridges:
   - If the notice is about Food Labs / Safety -> Look for 'Responsible Sourcing' or 'Business Partner' policies.
   - If the notice is about Digital Payments / E-Mandates -> Look for 'Information Security' policy.
   - If the notice is about FEMA / Foreign Exchange -> Look for 'Risk Management' policy.
   - If the notice is about Social Stock Exchange / NPOs -> Look for 'Corporate Social Responsibility' policy.
3. You MUST reason step-by-step about how the notice impacts the policies based on the cheat sheet above.
4. YOUR OUTPUT MUST START WITH THE EXACT WORD: <think>
5. If you determine there is absolutely no logical overlap, your final output after the think block MUST be exactly: [IRRELEVANT]
6. If there is a logical match, output your response EXACTLY in the following format:

Executive Summary: [1 sentence summarizing the new government mandate]
Policy Match: [The exact name of the Eternal/Zomato policy affected]
Required Changes / Gap Analysis: [Identify the EXACT clauses in the company policy that are missing the new government mandate. Be highly specific.]
Business Impact: [The operational or legal risk to Eternal Limited if they do not update this policy]
"""
    
    try:
        response_stream = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            stream=True
        )
        
        full_response = ""
        for chunk in response_stream:
            content = chunk['message']['content']
            print(content, end='', flush=True)
            full_response += content
            
        print("\n")
        return full_response
    except Exception as e:
        print(f"\nError communicating with Ollama model '{OLLAMA_MODEL}': {e}")
        return None

def save_memo(filepath, response_text):
    """Clean out reasoning tags and save memo as Markdown."""
    try:
        clean_memo = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
        
        if not clean_memo:
            clean_memo = response_text.strip()
            
        filename = os.path.basename(filepath)
        memo_name = os.path.splitext(filename)[0] + ".md"
        memo_path = os.path.join(MEMO_DIR, memo_name)
        
        with open(memo_path, "w", encoding="utf-8") as f:
            f.write(clean_memo)
            
        print(f"✅ Memo saved successfully to: {memo_path}")
    except Exception as e:
        print(f"Error saving memo for {filepath}: {e}")

def main():
    print("Starting Verifin Core Intelligence Engine...\n")
    
    if not os.path.exists(DOWNLOADED_DIR):
        print(f"Directory {DOWNLOADED_DIR} not found. Please run the scraper first.")
        return
        
    pdf_files = glob.glob(os.path.join(DOWNLOADED_DIR, "*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {DOWNLOADED_DIR}.")
        return
        
    print(f"Found {len(pdf_files)} PDF notices. Commencing analysis pipeline...\n")
    
    for pdf_file in pdf_files:
        print(f"\n{'='*60}\nProcessing: {os.path.basename(pdf_file)}\n{'='*60}")
        
        print("1. Extracting full text from PDF...")
        pdf_text = extract_pdf_text(pdf_file)
        if not pdf_text:
            print("Skipping to next file due to extraction failure.")
            continue
            
        print("2. Retrieving Policy contexts via Multi-Probe Vector Search...")
        lowest_distance, context = retrieve_zomato_policies(pdf_text)
        
        if lowest_distance is not None and lowest_distance > DISTANCE_THRESHOLD:
            print(f"Notice mathematically rejected. No relevant policies found (Distance: {lowest_distance:.4f}). Skipping LLM analysis.")
            continue
            
        if not context:
            print("Warning: No coherent policy context found in Vector DB or DB connection failed.")
            
        print(f"-> Successfully mapped semantic relationship! (Best Distance: {lowest_distance:.4f})")
        print("3. Generating Compliance Memo (Ollama Analysis Stream)...\n")
        response_text = generate_compliance_memo(pdf_text, context)
        
        if response_text and "[IRRELEVANT]" in response_text.upper():
            print("Notice is logically irrelevant to provided policies. Aborting memo generation.")
            continue
            
        if response_text:
            print("4. Saving Output Memo...")
            save_memo(pdf_file, response_text)

if __name__ == "__main__":
    main()