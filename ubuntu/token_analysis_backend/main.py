import os
import shutil
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging
from dotenv import load_dotenv
import uuid
from fastapi.responses import JSONResponse

# Use absolute import for script execution
from extraction_processor import extract_token_information_iteratively, load_documents_from_sources, TokenAnalysisSchema

# Configure logging (consistent with extraction_processor)
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
UPLOAD_DIRECTORY = os.path.join(os.path.dirname(__file__), 'upload_temp')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=os.path.join(LOG_DIR, 'backend_process.log'),
    filemode='a'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS configuration
origins = [
    "https://tokenlegal.vercel.app",
    "http://localhost",
    "http://localhost:3000", # Default Next.js dev port
    "http://localhost:3001", # Additional port for frontend
    "https://3004-i2xvk40ljk7wu7gh9cpss-0e4fe86c.manus.computer" # Exposed frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

job_status = {}

@app.post("/analyze/")
async def analyze_documents(
    files: Optional[List[UploadFile]] = File(None),
    urls: Optional[List[str]] = Form(None),
    token_name: Optional[str] = Form(None),
    token_symbol: Optional[str] = Form(None),
    token_type_methodology: Optional[str] = Form(None),
    additional_context: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None
):
    job_id = str(uuid.uuid4())
    job_status[job_id] = {"status": "Received", "details": "Starting analysis..."}
    background_tasks.add_task(
        process_documents_job,
        files, urls, token_name, token_symbol, token_type_methodology, additional_context, job_id
    )
    return {"job_id": job_id}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    return job_status.get(job_id, {"status": "Unknown job_id"})

# Helper to save uploaded files and process in background
def process_documents_job(files, urls, token_name, token_symbol, token_type_methodology, additional_context, job_id):
    try:
        job_status[job_id] = {"status": "Saving files", "details": "Saving uploaded files..."}
        file_paths = []
        urls_to_process = []
        processed_doc_sources = []
        if files:
            for file in files:
                file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
                with open(file_location, "wb+") as file_object:
                    shutil.copyfileobj(file.file, file_object)
                file_paths.append(file_location)
                processed_doc_sources.append({"name": file.filename, "type": "file"})
        if urls:
            urls_to_process.extend(urls)
            for u in urls:
                processed_doc_sources.append({"name": u, "type": "url"})
        job_status[job_id] = {"status": "Loading documents", "details": f"Loading {len(file_paths)} files and {len(urls_to_process)} URLs..."}
        documents = load_documents_from_sources(file_paths=file_paths, urls=urls_to_process if urls_to_process else None)
        if not documents:
            job_status[job_id] = {"status": "Error", "details": "No documents could be loaded from the provided sources."}
            return
        job_status[job_id] = {"status": "Extracting", "details": "Extracting token information..."}
        analysis_result = extract_token_information_iteratively(
            documents=documents,
            token_name=token_name,
            token_symbol=token_symbol,
            token_type_methodology=token_type_methodology,
            additional_context=additional_context
        )
        job_status[job_id] = {"status": "Complete", "details": "Extraction complete.", "result": analysis_result.model_dump()}
        # Clean up uploaded files
        for file_path in file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
    except Exception as e:
        job_status[job_id] = {"status": "Error", "details": str(e)}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting backend server with Uvicorn for local testing.")
    # Note: For actual deployment via pm2 or similar, this __main__ block might not be used directly.
    # The command `uvicorn main:app --host 0.0.0.0 --port 8000 --reload` would be used.
    uvicorn.run(app, host="0.0.0.0", port=8000)

