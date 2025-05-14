import os
import shutil
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging
from dotenv import load_dotenv

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

@app.post("/analyze/", response_model=TokenAnalysisSchema)
async def analyze_documents(
    files: Optional[List[UploadFile]] = File(None),
    url: Optional[str] = Form(None),
    token_name: Optional[str] = Form(None),
    token_symbol: Optional[str] = Form(None),
    token_type_methodology: Optional[str] = Form(None),
    additional_context: Optional[str] = Form(None)
):
    logger.info(f"Received analysis request: token_name={token_name}, files_present={bool(files)}, url_present={bool(url)}")
    file_paths = []
    urls_to_process = []
    processed_doc_sources = []

    if not files and not url:
        logger.error("No files or URL provided for analysis.")
        raise HTTPException(status_code=400, detail="No files or URL provided.")

    try:
        if files:
            for file in files:
                file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
                with open(file_location, "wb+") as file_object:
                    shutil.copyfileobj(file.file, file_object)
                file_paths.append(file_location)
                logger.info(f"File saved to {file_location}")
                processed_doc_sources.append({"name": file.filename, "type": "file"})

        if url:
            urls_to_process.append(url)
            logger.info(f"URL received: {url}")
            processed_doc_sources.append({"name": url, "type": "url"})

        documents = load_documents_from_sources(file_paths=file_paths, urls=urls_to_process if urls_to_process else None)
        
        if not documents:
            logger.error("No documents could be loaded from the provided sources.")
            raise HTTPException(status_code=400, detail="Could not load documents from provided sources.")

        logger.info("Starting iterative extraction process.")
        analysis_result = extract_token_information_iteratively(
            documents=documents,
            token_name=token_name,
            token_symbol=token_symbol,
            token_type_methodology=token_type_methodology,
            additional_context=additional_context
        )
        logger.info("Iterative extraction completed successfully.")
        
        # Clean up uploaded files if they exist
        for file_path in file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up uploaded file: {file_path}")
        
        return analysis_result

    except HTTPException as http_exc:
        logger.error(f"HTTPException during analysis: {http_exc.detail}")
        raise http_exc # Re-raise HTTPException
    except Exception as e:
        logger.error(f"An unexpected error occurred during analysis: {str(e)}", exc_info=True)
        # Clean up uploaded files in case of error
        for file_path in file_paths:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up uploaded file after error: {file_path}")
                except Exception as cleanup_e:
                    logger.error(f"Error during cleanup of file {file_path}: {cleanup_e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting backend server with Uvicorn for local testing.")
    # Note: For actual deployment via pm2 or similar, this __main__ block might not be used directly.
    # The command `uvicorn main:app --host 0.0.0.0 --port 8000 --reload` would be used.
    uvicorn.run(app, host="0.0.0.0", port=8000)

