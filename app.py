from fastapi import FastAPI, Form, Request, Response, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
import uvicorn
import os
import aiofiles
import json
import csv
import uuid
import re
import time
from src.helper import llm_pipeline

# ───────────────────────────────────────────────
# FastAPI App & Templates
# ───────────────────────────────────────────────
app = FastAPI(title="UN SDG Document Analyzer")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ───────────────────────────────────────────────
# Enhanced job tracking with progress
# ───────────────────────────────────────────────
jobs = {}

def clean_filename(filename):
    """
    Clean and format filename for professional use
    """
    name_without_ext = os.path.splitext(filename)[0]
    cleaned = re.sub(r'[^\w\s-]', '', name_without_ext)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip().title()
    professional_name = f"{cleaned} - Interview Questions and Answers"
    return professional_name

def clean_text(text):
    """
    Remove markdown formatting and special characters from text
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Remove markdown formatting
    text = re.sub(r'[\*\_\`]', '', text)
    
    # Remove any remaining numbering at start (like "53*")
    text = re.sub(r'^\s*\d+[\*\.]\s*', '', text)
    
    # Remove quotes that wrap entire content
    text = re.sub(r'^\"(.*)\"$', r'\1', text)
    text = re.sub(r"^\'(.*)\'$", r'\1', text)
    
    # Clean up quotes and extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Ensure proper sentence casing
    if text and len(text) > 1:
        text = text[0].upper() + text[1:]
    
    return text

def generate_csv(file_path: str, job_id: str, original_filename: str):
    """
    Blocking CSV generation function with progress tracking
    """
    try:
        print(f"DEBUG: Starting processing for job {job_id}")
        
        # Ensure job exists and update status
        if job_id not in jobs:
            print(f"DEBUG: Job {job_id} not found in jobs dictionary")
            return
            
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 5
        print(f"DEBUG: Job {job_id} status set to processing")
        
        # Get the pipeline components
        result = llm_pipeline(file_path)
        
        # Extract the chain and questions
        if len(result) >= 2:
            answer_generation_chain = result[0]
            ques_list = result[1]
            retriever = result[2] if len(result) > 2 else None
            llm_answer_gen = result[3] if len(result) > 3 else None
            
            print(f"DEBUG: Got {len(ques_list)} questions")
            
            # Limit questions for performance
            if len(ques_list) > 45:
                print(f"DEBUG: Limiting from {len(ques_list)} to 45 questions")
                ques_list = ques_list[:45]
                
        else:
            error_msg = f"llm_pipeline returned only {len(result)} values, expected at least 2"
            print(f"ERROR: {error_msg}")
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = error_msg
            return
        
        # Initialize progress tracking
        total_questions = len(ques_list)
        jobs[job_id]["total_questions"] = total_questions
        jobs[job_id]["current_question"] = 0
        jobs[job_id]["progress"] = 10
        
        print(f"Starting processing of {total_questions} questions...")

        output_dir = 'static/output/'
        os.makedirs(output_dir, exist_ok=True)
        
        # Create professional filename
        professional_name = clean_filename(original_filename)
        output_file = os.path.join(output_dir, f"{professional_name}.csv")
        
        # If file already exists, add a counter
        counter = 1
        base_output_file = output_file
        while os.path.exists(output_file):
            output_file = base_output_file.replace('.csv', f' ({counter}).csv')
            counter += 1

        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(["No.", "Question", "Answer"])

            for i, question in enumerate(ques_list):
                print(f"Processing question {i+1}/{total_questions}")
                
                # Update progress
                progress = int(((i + 1) / total_questions) * 100)  # 0-100%
                jobs[job_id]["current_question"] = i + 1
                jobs[job_id]["progress"] = progress
                
                # Clean the question
                clean_question = clean_text(question)
                
                # Get answer
                try:
                    response = answer_generation_chain.invoke({"input": clean_question})
                    
                    if isinstance(response, dict):
                        answer = response.get("answer") or response.get("output") or response.get("result") or str(response)
                    else:
                        answer = str(response)
                    
                    clean_answer = clean_text(answer.strip())
                    print(f"DEBUG: Got answer for question {i+1}")
                    
                except Exception as e:
                    print(f"DEBUG: Error getting answer: {e}")
                    clean_answer = "Not found in context."
                
                # Store current Q&A
                jobs[job_id]["current_qa"] = {
                    "index": i + 1,
                    "question": clean_question,
                    "answer": clean_answer
                }
                
                # Write to CSV
                csv_writer.writerow([i + 1, clean_question, clean_answer])
                
                # Small delay to prevent rate limiting
                if i < len(ques_list) - 1:
                    time.sleep(2)

        # Final update
        jobs[job_id]["status"] = "done"
        jobs[job_id]["file"] = output_file
        jobs[job_id]["progress"] = 100
        jobs[job_id]["current_qa"] = None
        
        print(f"DEBUG: Job {job_id} completed successfully")
        print(f"CSV generated: {output_file}")

    except Exception as e:
        print(f"ERROR in generate_csv: {e}")
        if job_id in jobs:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)
        import traceback
        traceback.print_exc()

# ───────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_pdf(pdf_file: bytes = File(...), filename: str = Form(...)):
    base_folder = 'static/docs/'
    os.makedirs(base_folder, exist_ok=True)
    pdf_filename = os.path.join(base_folder, filename)

    async with aiofiles.open(pdf_filename, 'wb') as f:
        await f.write(pdf_file)

    return Response(
        jsonable_encoder(json.dumps({"msg": "success", "pdf_filename": pdf_filename}))
    )

@app.post("/analyze")
async def analyze(pdf_filename: str = Form(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    if not os.path.exists(pdf_filename):
        return Response(
            jsonable_encoder(json.dumps({"error": "PDF file not found."})), 
            status_code=400
        )

    job_id = str(uuid.uuid4())
    
    # Extract original filename
    original_filename = os.path.basename(pdf_filename)
    
    # Initialize job with progress tracking
    jobs[job_id] = {
        "status": "queued", 
        "file": None,
        "progress": 0,
        "total_questions": 0,
        "current_question": 0,
        "current_qa": None,
        "error": None
    }
    
    print(f"DEBUG: Created job {job_id} for file {original_filename}")
    print(f"DEBUG: Current jobs: {list(jobs.keys())}")
    
    # Add background task
    background_tasks.add_task(generate_csv, pdf_filename, job_id, original_filename)

    return Response(
        jsonable_encoder(json.dumps({"job_id": job_id, "status": "queued"}))
    )

@app.get("/status/{job_id}")
async def job_status(job_id: str):
    print(f"DEBUG: Status check for job {job_id}")
    print(f"DEBUG: Available jobs: {list(jobs.keys())}")
    
    job = jobs.get(job_id)
    if not job:
        print(f"DEBUG: Job {job_id} not found!")
        return Response(
            jsonable_encoder(json.dumps({"error": "Job ID not found."})),
            status_code=404
        )
    
    response_data = {
        "job_id": job_id, 
        "status": job["status"],
        "progress": job["progress"],
        "current_question": job["current_question"],
        "total_questions": job["total_questions"]
    }
    
    # Include current Q&A for real-time display
    if job.get("current_qa"):
        response_data["current_qa"] = job["current_qa"]
    
    # Include file path when job is done
    if job["status"] == "done" and job.get("file"):
        response_data["file"] = job["file"]
        professional_name = os.path.basename(job["file"])
        response_data["download_filename"] = professional_name
    
    # Include error if failed
    if job["status"] == "failed" and job.get("error"):
        response_data["error"] = job["error"]
    
    print(f"DEBUG: Returning status for job {job_id}: {job['status']}")
    return Response(jsonable_encoder(json.dumps(response_data)))

# ───────────────────────────────────────────────
# Run Server
# ───────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("app:app", host='127.0.0.1', port=8080, reload=False)
