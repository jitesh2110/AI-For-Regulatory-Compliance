import os
import re
import chromadb
from PyPDF2 import PdfReader
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIRECTORY = os.path.join(BASE_DIR, "Policies documents")
DB_PATH = os.path.join(BASE_DIR, "Zomato_DB")
COLLECTION_NAME = "Zomato"

# 1. Initialize the Advanced Local Embedding Model (BGE-Large)
print("Loading the high-dimension embedding model (BAAI/bge-large-en-v1.5)...")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-large-en-v1.5")

# 2. Initialize ChromaDB
print(f"Initializing ChromaDB locally at: {DB_PATH}")
chroma_client = chromadb.PersistentClient(path=DB_PATH)

# 3. Create or Get the "Zomato" Collection
try:
    chroma_client.delete_collection(name=COLLECTION_NAME)
    print("🗑️ Cleared old database collection to ensure fresh data ingestion.")
except Exception:
    pass

collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=sentence_transformer_ef
)

# 4. Configure the Smart Splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)

def process_directory(directory_path):
    pdf_files = [f for f in os.listdir(directory_path) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"❌ No PDF files found in {directory_path}.")
        return

    print(f"✅ Found {len(pdf_files)} PDF(s). Starting extraction and embedding pipeline...\n")

    for filename in pdf_files:
        file_path = os.path.join(directory_path, filename)
        policy_name = os.path.splitext(filename)[0] 
        print(f"Processing: {policy_name}")
        
        try:
            reader = PdfReader(file_path)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n" 
                    
            if not full_text.strip():
                print(f"  -> ⚠️ Warning: No text extracted. The PDF might be a scanned image.")
                continue
                
            # Smart text cleaning
            clean_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', full_text)
            clean_text = re.sub(r' {2,}', ' ', clean_text).strip()
            
            chunks = text_splitter.split_text(clean_text)
            valid_chunks = [chunk.strip() for chunk in chunks if len(chunk.strip()) > 50]
            
            if not valid_chunks:
                print(f"  -> ⚠️ Warning: No valid chunks generated for this file.")
                continue
            
            documents = []
            metadata = []
            ids = []
            
            for i, chunk in enumerate(valid_chunks):
                documents.append(chunk)
                metadata.append({"source": policy_name, "chunk_index": i})
                ids.append(f"{policy_name}_chunk_{i}")
                
            collection.add(
                documents=documents,
                metadatas=metadata,
                ids=ids
            )
            print(f"  -> ✅ Successfully stored {len(valid_chunks)} chunks.")
            
        except Exception as e:
            print(f"  -> ❌ Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    if os.path.exists(PDF_DIRECTORY):
        process_directory(PDF_DIRECTORY)
        print("\n🚀 Pipeline Complete: All policies have been successfully embedded and stored in ChromaDB!")
    else:
        print(f"❌ Error: The directory '{PDF_DIRECTORY}' does not exist. Please check the folder path.")