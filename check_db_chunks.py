import os
import chromadb

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "Zomato_DB")
COLLECTION_NAME = "Zomato"

def print_db_chunks():
    print(f"Connecting to ChromaDB at: {DB_PATH}")
    try:
        # Initialize ChromaDB client
        chroma_client = chromadb.PersistentClient(path=DB_PATH)
        
        # Get the collection
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
        
        # Fetch items in the collection
        # Note: .get() fetches all items if no specific IDs are passed
        results = collection.get(
            include=['documents', 'metadatas']
        )
        
        documents = results.get('documents', [])
        metadatas = results.get('metadatas', [])
        ids = results.get('ids', [])
        
        total_chunks = len(documents)
        print(f"\n✅ Successfully connected! Found {total_chunks} total chunks in the '{COLLECTION_NAME}' collection.\n")
        
        if total_chunks == 0:
            print("The database is currently empty. Run build_zomato_db.py first.")
            return

        # Limit how many chunks to print so we don't flood the terminal
        limit = min(10, total_chunks) 
        print(f"--- Printing the first {limit} chunks for review ---\n")
        
        for i in range(limit):
            doc_id = ids[i]
            meta = metadatas[i]
            text = documents[i]
            
            print(f"[{i+1}/{limit}] CHUNK ID: {doc_id}")
            print(f"Source Policy: {meta.get('source', 'Unknown')}")
            print(f"Chunk Index: {meta.get('chunk_index', 'Unknown')}")
            print("-" * 60)
            print(text)
            print("=" * 60 + "\n")
            
        if total_chunks > limit:
            print(f"... plus {total_chunks - limit} more chunks hiding in the database.")
            print("(To see more, change the 'limit' variable in the script).")
            
    except Exception as e:
        print(f"❌ Error connecting to database or fetching chunks: {e}")

if __name__ == "__main__":
    print_db_chunks()