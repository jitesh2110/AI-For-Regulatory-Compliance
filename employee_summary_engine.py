import os
import glob
import json
import PyPDF2
import ollama
import re

# --- PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTICES_DIR = os.path.join(BASE_DIR, "downloaded_notices") # Strictly set to downloaded_notices
OUTPUT_DIR = os.path.join(BASE_DIR, "employee_summaries")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def parse_llm_output(output):
    # Remove think blocks
    text = re.sub(r'<think>.*?</think>', '', output, flags=re.DOTALL).strip()
    
    # Parse sections using regex
    summary_match = re.search(r'SUMMARY:(.*?)(?:IMPACT:|BENEFITS:|FLASH_ALERTS:|$)', text, re.DOTALL | re.IGNORECASE)
    impact_match = re.search(r'IMPACT:(.*?)(?:BENEFITS:|FLASH_ALERTS:|$)', text, re.DOTALL | re.IGNORECASE)
    benefits_match = re.search(r'BENEFITS:(.*?)(?:FLASH_ALERTS:|$)', text, re.DOTALL | re.IGNORECASE)
    alerts_match = re.search(r'FLASH_ALERTS:(.*)', text, re.DOTALL | re.IGNORECASE)
    
    summary = summary_match.group(1).strip() if summary_match else "N/A"
    impact = impact_match.group(1).strip() if impact_match else "N/A"
    benefits = benefits_match.group(1).strip() if benefits_match else "N/A"
    
    flash_alerts = []
    if alerts_match:
        alerts_text = alerts_match.group(1).strip()
        for line in alerts_text.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                flash_alerts.append(line.lstrip('-* ').strip())
                
    return {
        "summary": summary,
        "impact": impact,
        "benefits": benefits,
        "flash_alerts": flash_alerts
    }

def main():
    print(f"\n🚀 Starting Employee Summary Engine...")
    print(f"📂 Looking for PDFs strictly in: {NOTICES_DIR}")
    
    ensure_dir(OUTPUT_DIR)
    
    if not os.path.exists(NOTICES_DIR):
        print(f"❌ Error: The directory '{NOTICES_DIR}' does not exist.")
        return

    pdf_files = glob.glob(os.path.join(NOTICES_DIR, "*.pdf"))
    if not pdf_files:
        print(f"❌ No PDFs found inside {NOTICES_DIR}. Make sure your scraper has run!")
        return

    print(f"✅ Found {len(pdf_files)} PDFs. Generating employee summaries...\n")

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        json_filename = filename.replace('.pdf', '.json')
        json_path = os.path.join(OUTPUT_DIR, json_filename)
        
        if os.path.exists(json_path):
            print(f"⏭️ Skipping {filename}, already processed.")
            continue
            
        print(f"⚙️ Processing {filename}...")
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                pdf_text = "".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
            
            # Truncate text to save RAM
            text_truncated = pdf_text[:10000]
            
            prompt = f"""You are a Corporate Communications Expert. Translate this complex government regulatory notice into simple, plain English for standard employees. Do not mention internal policies. 
Your output MUST follow this exact format:
<think>...your reasoning...</think>
SUMMARY: [2-3 sentences explaining the notice simply]
IMPACT: [How this changes day-to-day operations]
BENEFITS: [Why this regulation is actually a good thing]
FLASH_ALERTS:
- [Short actionable bullet point 1]
- [Short actionable bullet point 2]

[NOTICE CONTENT]
{text_truncated}
"""
            
            response = ollama.chat(
                model='deepseek-r1',
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            output_content = response['message']['content']
            parsed_data = parse_llm_output(output_content)
            parsed_data["filename"] = filename
            
            with open(json_path, 'w', encoding='utf-8') as jf:
                json.dump(parsed_data, jf, indent=4)
                
            print(f"✅ Saved parsed summary to {json_filename}\n")
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")

    print("🎉 All summaries generated successfully!")

if __name__ == "__main__":
    main()