# from fastapi import FastAPI, Form, Request, Response, File, BackgroundTasks
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
# from fastapi.encoders import jsonable_encoder
# import uvicorn
# import os
# import aiofiles
# import json
# import csv
# import uuid
# import re
# from src.helper import llm_pipeline

# # ───────────────────────────────────────────────
# # FastAPI App & Templates
# # ───────────────────────────────────────────────
# app = FastAPI(title="UN SDG Document Analyzer")
# app.mount("/static", StaticFiles(directory="static"), name="static")
# templates = Jinja2Templates(directory="templates")

# # ───────────────────────────────────────────────
# # Enhanced job tracking with progress
# # ───────────────────────────────────────────────
# jobs = {}  # {
# #   job_id: {
# #       "status": "queued"/"processing"/"done"/"failed", 
# #       "file": "path/to/file.csv",
# #       "progress": 0,
# #       "total_questions": 0,
# #       "current_question": 0,
# #       "current_qa": None
# #   }
# # }

# def clean_filename(filename):
#     """
#     Clean and format filename for professional use
#     """
#     # Remove file extension
#     name_without_ext = os.path.splitext(filename)[0]
    
#     # Remove special characters and replace with spaces
#     cleaned = re.sub(r'[^\w\s-]', '', name_without_ext)
    
#     # Replace multiple spaces with single space
#     cleaned = re.sub(r'\s+', ' ', cleaned)
    
#     # Trim and title case
#     cleaned = cleaned.strip().title()
    
#     # Add professional suffix
#     professional_name = f"{cleaned} - Interview Questions and Answers"
    
#     return professional_name

# def clean_text(text):
#     """
#     Remove markdown formatting and special characters from text
#     """
#     if not isinstance(text, str):
#         text = str(text)
    
#     # Remove markdown formatting
#     text = re.sub(r'[\*\_\`]', '', text)
    
#     # Remove any remaining numbering at start (like "53*")
#     text = re.sub(r'^\s*\d+[\*\.]\s*', '', text)
    
#     # Clean up quotes and extra spaces
#     text = re.sub(r'\s+', ' ', text).strip()
    
#     # Ensure proper sentence casing
#     if text and len(text) > 1:
#         text = text[0].upper() + text[1:]
    
#     return text

# def generate_csv(file_path: str, job_id: str, original_filename: str):
#     """
#     Blocking CSV generation function with progress tracking
#     """
#     def clean_text(text):
#         """
#         Remove markdown formatting and special characters from text
#         """
#         if not isinstance(text, str):
#             text = str(text)
        
#         # Remove markdown formatting
#         text = re.sub(r'[\*\_\`]', '', text)
        
#         # Remove any remaining numbering at start (like "53*")
#         text = re.sub(r'^\s*\d+[\*\.]\s*', '', text)
        
#         # Remove quotes that wrap entire content
#         text = re.sub(r'^\"(.*)\"$', r'\1', text)
#         text = re.sub(r"^\'(.*)\'$", r'\1', text)
        
#         # Clean up quotes and extra spaces
#         text = re.sub(r'\s+', ' ', text).strip()
        
#         # Ensure proper sentence casing
#         if text and len(text) > 1:
#             text = text[0].upper() + text[1:]
        
#         return text

#     try:
#         jobs[job_id]["status"] = "processing"
        
#         # Get the pipeline components
#         result = llm_pipeline(file_path)
        
#         # Extract the chain and questions
#         if len(result) >= 2:
#             answer_generation_chain = result[0]
#             ques_list = result[1]
#             # We might also need the retriever for context
#             retriever = result[2] if len(result) > 2 else None
#             llm_answer_gen = result[3] if len(result) > 3 else None
            
#             print(f"DEBUG: llm_pipeline returned {len(result)} values")
#             print(f"DEBUG: Got {len(ques_list)} questions")
#             print(f"DEBUG: First 3 questions:")
#             for i, q in enumerate(ques_list[:3]):
#                 print(f"  Q{i+1}: {q}")
#         else:
#             raise ValueError(f"llm_pipeline returned only {len(result)} values, expected at least 2")
        
#         # Initialize progress tracking
#         total_questions = len(ques_list)
#         jobs[job_id]["total_questions"] = total_questions
#         jobs[job_id]["current_question"] = 0
#         jobs[job_id]["progress"] = 0
        
#         print(f"Starting processing of {total_questions} questions...")

#         output_dir = 'static/output/'
#         os.makedirs(output_dir, exist_ok=True)
        
#         # Create professional filename based on original PDF
#         professional_name = clean_filename(original_filename)
#         output_file = os.path.join(output_dir, f"{professional_name}.csv")
        
#         # If file already exists, add a counter
#         counter = 1
#         base_output_file = output_file
#         while os.path.exists(output_file):
#             output_file = base_output_file.replace('.csv', f' ({counter}).csv')
#             counter += 1

#         with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
#             csv_writer = csv.writer(csvfile)
#             csv_writer.writerow(["No.", "Question", "Answer"])  # Header with numbering

#             for i, question in enumerate(ques_list):
#                 print(f"Processing question {i+1}/{total_questions}: {question}")
                
#                 # Update current question and progress
#                 jobs[job_id]["current_question"] = i + 1
#                 progress = int(((i + 1) / total_questions) * 100)
#                 jobs[job_id]["progress"] = progress
                
#                 # Clean the question first
#                 clean_question = clean_text(question)
                
#                 # CORRECTED: Use the retrieval chain properly
#                 try:
#                     # The retrieval chain expects {"input": question} and returns dict with "answer" key
#                     response = answer_generation_chain.invoke({"input": clean_question})
                    
#                     # DEBUG: Print the response structure to understand what we're getting
#                     print(f"DEBUG: Response type: {type(response)}")
#                     if isinstance(response, dict):
#                         print(f"DEBUG: Response keys: {response.keys()}")
                    
#                     # Extract the answer from the response - handle different response formats
#                     if isinstance(response, dict):
#                         # Try different possible keys that might contain the answer
#                         answer = response.get("answer") or response.get("output") or response.get("result") or str(response)
#                     else:
#                         answer = str(response)
                    
#                     # Clean the answer text
#                     clean_answer = clean_text(answer.strip())
                        
#                     print("DEBUG: Retrieval chain succeeded!")
#                     print(f"DEBUG: Clean Answer: {clean_answer}")
                    
#                 except Exception as e1:
#                     print(f"DEBUG: Retrieval chain failed: {e1}")
                    
#                     # Fallback: If retrieval chain fails, try manual retrieval + answer generation
#                     try:
#                         if retriever and llm_answer_gen:
#                             from langchain_classic.chains.combine_documents import create_stuff_documents_chain
#                             from langchain_core.prompts import PromptTemplate
                            
#                             # Manual retrieval
#                             retrieved_docs = retriever.invoke(clean_question)
#                             context = "\n\n".join([doc.page_content for doc in retrieved_docs])
                            
#                             # Create answer prompt
#                             ANSWER_PROMPT = PromptTemplate.from_template(
#                                 """You are an expert on UN Sustainable Development Goals (SDGs).
#                                 Your task is to extract and summarize the answer to the question using ONLY the provided CONTEXT.

#                                 **RULES:**
#                                 1.  **Strict Context Reliance:** Use ONLY the provided CONTEXT. Do NOT invent facts or generalize.
#                                 2.  **Focus:** Directly extract the specific requirement or characteristic requested by the question from the relevant SDG Target in the context.
#                                 3.  **No Citation:** Do NOT include 'Target X.Y', 'Goal X', or any reference/citation in the final answer.
#                                 4.  **Conciseness:** Provide a brief and precise answer, avoiding unnecessary elaboration.
#                                 5.  **No Markdown:** Do NOT use any markdown formatting like *, **, `, or _ in your response.
#                                 6.  **Plain Text Only:** Use only plain text with proper punctuation.
#                                 7.  **Failure State:** If the exact answer is not present in the context, reply exactly: **Not found in context.**

#                                 Context: {context}

#                                 Question: {input}

#                                 Answer in format: [Directly extracted answer/summary]."""
#                             )
                            
#                             # Create and invoke the chain
#                             combine_chain = create_stuff_documents_chain(llm_answer_gen, ANSWER_PROMPT)
#                             response = combine_chain.invoke({"input": clean_question, "context": context})
                            
#                             if isinstance(response, dict):
#                                 clean_answer = response.get("output") or response.get("answer") or str(response)
#                             else:
#                                 clean_answer = str(response)
                            
#                             clean_answer = clean_text(clean_answer.strip())
#                             print("DEBUG: Method 2 (manual retrieval) succeeded!")
#                         else:
#                             raise Exception("Retriever or LLM not available")
#                     except Exception as e2:
#                         print(f"DEBUG: Method 2 failed: {e2}")
#                         clean_answer = f"Error generating answer: {e2}"
                
#                 print(f"Answer: {clean_answer}")
#                 print("--------------------------------------------------\n\n")
                
#                 # Store current Q&A for real-time display WITH CLEANED TEXT
#                 jobs[job_id]["current_qa"] = {
#                     "index": i + 1,
#                     "question": clean_question,
#                     "answer": clean_answer
#                 }
                
#                 # Write to CSV with numbering and CLEANED TEXT
#                 csv_writer.writerow([i + 1, clean_question, clean_answer])

#         # Final update
#         jobs[job_id]["status"] = "done"
#         jobs[job_id]["file"] = output_file
#         jobs[job_id]["progress"] = 100
#         jobs[job_id]["current_qa"] = None  # Clear current Q&A
        
#         print(f"CSV generated successfully: {output_file}")

#     except Exception as e:
#         jobs[job_id]["status"] = "failed"
#         jobs[job_id]["error"] = str(e)
#         print(f"Error generating CSV: {e}")
#         import traceback
#         traceback.print_exc()  # This will print the full traceback

# # ───────────────────────────────────────────────
# # Routes
# # ───────────────────────────────────────────────
# @app.get("/")
# async def index(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})

# @app.post("/upload")
# async def upload_pdf(pdf_file: bytes = File(...), filename: str = Form(...)):
#     base_folder = 'static/docs/'
#     os.makedirs(base_folder, exist_ok=True)
#     pdf_filename = os.path.join(base_folder, filename)

#     async with aiofiles.open(pdf_filename, 'wb') as f:
#         await f.write(pdf_file)

#     return Response(
#         jsonable_encoder(json.dumps({"msg": "success", "pdf_filename": pdf_filename}))
#     )

# def generate_csv(file_path: str, job_id: str, original_filename: str):
#     """
#     Blocking CSV generation function with progress tracking
#     """
#     try:
#         jobs[job_id]["status"] = "processing"
        
#         # Get the pipeline components
#         result = llm_pipeline(file_path)
        
#         # Extract the chain and questions
#         if len(result) >= 2:
#             answer_generation_chain = result[0]
#             ques_list = result[1]
#             # We might also need the retriever for context
#             retriever = result[2] if len(result) > 2 else None
#             llm_answer_gen = result[3] if len(result) > 3 else None
            
#             print(f"Note: llm_pipeline returned {len(result)} values")
#         else:
#             raise ValueError(f"llm_pipeline returned only {len(result)} values, expected at least 2")
        
#         # Initialize progress tracking
#         total_questions = len(ques_list)
#         jobs[job_id]["total_questions"] = total_questions
#         jobs[job_id]["current_question"] = 0
#         jobs[job_id]["progress"] = 0
        
#         print(f"Starting processing of {total_questions} questions...")

#         output_dir = 'static/output/'
#         os.makedirs(output_dir, exist_ok=True)
        
#         # Create professional filename based on original PDF
#         professional_name = clean_filename(original_filename)
#         output_file = os.path.join(output_dir, f"{professional_name}.csv")
        
#         # If file already exists, add a counter
#         counter = 1
#         base_output_file = output_file
#         while os.path.exists(output_file):
#             output_file = base_output_file.replace('.csv', f' ({counter}).csv')
#             counter += 1

#         with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
#             csv_writer = csv.writer(csvfile)
#             csv_writer.writerow(["No.", "Question", "Answer"])  # Header with numbering

#             for i, question in enumerate(ques_list):
#                 print(f"Processing question {i+1}/{total_questions}: {question}")
                
#                 # Update current question and progress
#                 jobs[job_id]["current_question"] = i + 1
#                 progress = int(((i + 1) / total_questions) * 100)
#                 jobs[job_id]["progress"] = progress
                
#                 # Use the correct input format for the retrieval chain
#                 try:
#                     # Method 1: Use the retrieval chain with just the question
#                     response = answer_generation_chain.invoke({"input": question})
                    
#                     # Extract the answer from the response
#                     if isinstance(response, dict):
#                         # The retrieval chain returns dict with "answer" key
#                         answer = response.get("answer", "")
#                     else:
#                         answer = str(response)
                        
#                     print("DEBUG: Method 1 (retrieval chain) succeeded!")
                    
#                 except Exception as e1:
#                     print(f"DEBUG: Method 1 failed: {e1}")
                    
#                     # Method 2: If retrieval chain fails, try manual retrieval + answer generation
#                     try:
#                         if retriever and llm_answer_gen:
#                             from langchain_classic.chains.combine_documents import create_stuff_documents_chain
#                             from langchain_core.prompts import PromptTemplate
                            
#                             # Manual retrieval
#                             retrieved_docs = retriever.invoke(question)
#                             context = "\n\n".join([doc.page_content for doc in retrieved_docs])
                            
#                             # Create answer prompt
#                             ANSWER_PROMPT = PromptTemplate.from_template(
#                                 """You are an expert on UN Sustainable Development Goals (SDGs).
#                                 Your task is to extract and summarize the answer to the question using ONLY the provided CONTEXT.

#                                 **RULES:**
#                                 1.  **Strict Context Reliance:** Use ONLY the provided CONTEXT. Do NOT invent facts or generalize.
#                                 2.  **Focus:** Directly extract the specific requirement or characteristic requested by the question from the relevant SDG Target in the context.
#                                 3.  **No Citation:** Do NOT include 'Target X.Y', 'Goal X', or any reference/citation in the final answer.
#                                 4.  **Failure State:** If the exact answer is not present in the context, reply exactly: **Not found in context.**

#                                 Context: {context}

#                                 Question: {input}

#                                 Answer in format: [Directly extracted answer/summary]."""
#                             )
                            
#                             # Create and invoke the chain
#                             combine_chain = create_stuff_documents_chain(llm_answer_gen, ANSWER_PROMPT)
#                             response = combine_chain.invoke({"input": question, "context": context})
#                             answer = str(response)
#                             print("DEBUG: Method 2 (manual retrieval) succeeded!")
#                         else:
#                             raise Exception("Retriever or LLM not available")
#                     except Exception as e2:
#                         print(f"DEBUG: Method 2 failed: {e2}")
#                         answer = f"Error generating answer: {e2}"
                
#                 # Ensure answer is a string
#                 if not isinstance(answer, str):
#                     try:
#                         answer = str(answer)
#                     except:
#                         answer = "Could not convert answer to string"
                
#                 print(f"Answer: {answer}")
#                 print("--------------------------------------------------\n\n")
                
#                 # Store current Q&A for real-time display WITH NUMBERING
#                 jobs[job_id]["current_qa"] = {
#                     "index": i + 1,
#                     "question": question,
#                     "answer": answer
#                 }
                
#                 # Write to CSV with numbering - Question No. starts from 1
#                 csv_writer.writerow([i + 1, question, answer])

#         # Final update
#         jobs[job_id]["status"] = "done"
#         jobs[job_id]["file"] = output_file
#         jobs[job_id]["progress"] = 100
#         jobs[job_id]["current_qa"] = None  # Clear current Q&A
        
#         print(f"CSV generated successfully: {output_file}")

#     except Exception as e:
#         jobs[job_id]["status"] = "failed"
#         jobs[job_id]["error"] = str(e)
#         print(f"Error generating CSV: {e}")
#         import traceback
#         traceback.print_exc()  # This will print the full traceback

# @app.post("/analyze")
# async def analyze(pdf_filename: str = Form(...), background_tasks: BackgroundTasks = BackgroundTasks()):
#     if not os.path.exists(pdf_filename):
#         return Response(
#             jsonable_encoder(json.dumps({"error": "PDF file not found."})), 
#             status_code=400
#         )

#     job_id = str(uuid.uuid4())
    
#     # Extract original filename from the pdf_filename path
#     original_filename = os.path.basename(pdf_filename)
    
#     # Initialize job with progress tracking
#     jobs[job_id] = {
#         "status": "queued", 
#         "file": None,
#         "progress": 0,
#         "total_questions": 0,
#         "current_question": 0,
#         "current_qa": None
#     }
    
#     # Add background task with original filename
#     background_tasks.add_task(generate_csv, pdf_filename, job_id, original_filename)

#     return Response(
#         jsonable_encoder(json.dumps({"job_id": job_id, "status": jobs[job_id]["status"]}))
#     )

# @app.get("/status/{job_id}")
# async def job_status(job_id: str):
#     job = jobs.get(job_id)
#     if not job:
#         return Response(
#             jsonable_encoder(json.dumps({"error": "Job ID not found."})),
#             status_code=404
#         )
    
#     response_data = {
#         "job_id": job_id, 
#         "status": job["status"],
#         "progress": job["progress"],
#         "current_question": job["current_question"],
#         "total_questions": job["total_questions"]
#     }
    
#     # Include current Q&A for real-time display
#     if job.get("current_qa"):
#         response_data["current_qa"] = job["current_qa"]
    
#     # Include file path when job is done
#     if job["status"] == "done" and job.get("file"):
#         response_data["file"] = job["file"]
        
#         # Also include the professional filename for download
#         professional_name = os.path.basename(job["file"])
#         response_data["download_filename"] = professional_name
    
#     return Response(jsonable_encoder(json.dumps(response_data)))

# # ───────────────────────────────────────────────
# # Run Server
# # ───────────────────────────────────────────────
# if __name__ == "__main__":
#     uvicorn.run("app:app", host='127.0.0.1', port=8080, reload=False)


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
jobs = {}  # {
#   job_id: {
#       "status": "queued"/"processing"/"done"/"failed", 
#       "file": "path/to/file.csv",
#       "progress": 0,
#       "total_questions": 0,
#       "current_question": 0,
#       "current_qa": None
#   }
# }

def clean_filename(filename):
    """
    Clean and format filename for professional use
    """
    # Remove file extension
    name_without_ext = os.path.splitext(filename)[0]
    
    # Remove special characters and replace with spaces
    cleaned = re.sub(r'[^\w\s-]', '', name_without_ext)
    
    # Replace multiple spaces with single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Trim and title case
    cleaned = cleaned.strip().title()
    
    # Add professional suffix
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
        jobs[job_id]["status"] = "processing"
        
        # Get the pipeline components
        result = llm_pipeline(file_path)
        
        # Extract the chain and questions
        if len(result) >= 2:
            answer_generation_chain = result[0]
            ques_list = result[1]
            # We might also need the retriever for context
            retriever = result[2] if len(result) > 2 else None
            llm_answer_gen = result[3] if len(result) > 3 else None
            
            print(f"DEBUG: llm_pipeline returned {len(result)} values")
            print(f"DEBUG: Got {len(ques_list)} questions")
            print(f"DEBUG: First 3 questions:")
            for i, q in enumerate(ques_list[:3]):
                print(f"  Q{i+1}: {q}")
        else:
            raise ValueError(f"llm_pipeline returned only {len(result)} values, expected at least 2")
        
        # Initialize progress tracking
        total_questions = len(ques_list)
        jobs[job_id]["total_questions"] = total_questions
        jobs[job_id]["current_question"] = 0
        jobs[job_id]["progress"] = 0
        
        print(f"Starting processing of {total_questions} questions...")

        output_dir = 'static/output/'
        os.makedirs(output_dir, exist_ok=True)
        
        # Create professional filename based on original PDF
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
            csv_writer.writerow(["No.", "Question", "Answer"])  # Header with numbering

            for i, question in enumerate(ques_list):
                print(f"Processing question {i+1}/{total_questions}: {question}")
                
                # Update current question and progress
                jobs[job_id]["current_question"] = i + 1
                progress = int(((i + 1) / total_questions) * 100)
                jobs[job_id]["progress"] = progress
                
                # Clean the question first
                clean_question = clean_text(question)
                
                # CORRECTED: Use the retrieval chain properly
                try:
                    # The retrieval chain expects {"input": question} and returns dict with "answer" key
                    response = answer_generation_chain.invoke({"input": clean_question})
                    
                    # DEBUG: Print the response structure to understand what we're getting
                    print(f"DEBUG: Response type: {type(response)}")
                    if isinstance(response, dict):
                        print(f"DEBUG: Response keys: {response.keys()}")
                    
                    # Extract the answer from the response - handle different response formats
                    if isinstance(response, dict):
                        # Try different possible keys that might contain the answer
                        answer = response.get("answer") or response.get("output") or response.get("result") or str(response)
                    else:
                        answer = str(response)
                    
                    # Clean the answer text
                    clean_answer = clean_text(answer.strip())
                        
                    print("DEBUG: Retrieval chain succeeded!")
                    print(f"DEBUG: Clean Answer: {clean_answer}")
                    
                except Exception as e1:
                    print(f"DEBUG: Retrieval chain failed: {e1}")
                    
                    # Fallback: If retrieval chain fails, try manual retrieval + answer generation
                    try:
                        if retriever and llm_answer_gen:
                            from langchain_classic.chains.combine_documents import create_stuff_documents_chain
                            from langchain_core.prompts import PromptTemplate
                            
                            # Manual retrieval
                            retrieved_docs = retriever.invoke(clean_question)
                            context = "\n\n".join([doc.page_content for doc in retrieved_docs])
                            
                            # Create answer prompt
                            ANSWER_PROMPT = PromptTemplate.from_template(
                                """You are an expert on UN Sustainable Development Goals (SDGs).
                                Your task is to extract and summarize the answer to the question using ONLY the provided CONTEXT.

                                **RULES:**
                                1.  **Strict Context Reliance:** Use ONLY the provided CONTEXT. Do NOT invent facts or generalize.
                                2.  **Focus:** Directly extract the specific requirement or characteristic requested by the question from the relevant SDG Target in the context.
                                3.  **No Citation:** Do NOT include 'Target X.Y', 'Goal X', or any reference/citation in the final answer.
                                4.  **Conciseness:** Provide a brief and precise answer, avoiding unnecessary elaboration.
                                5.  **No Markdown:** Do NOT use any markdown formatting like *, **, `, or _ in your response.
                                6.  **Plain Text Only:** Use only plain text with proper punctuation.
                                7.  **Failure State:** If the exact answer is not present in the context, reply exactly: **Not found in context.**

                                Context: {context}

                                Question: {input}

                                Answer in format: [Directly extracted answer/summary]."""
                            )
                            
                            # Create and invoke the chain
                            combine_chain = create_stuff_documents_chain(llm_answer_gen, ANSWER_PROMPT)
                            response = combine_chain.invoke({"input": clean_question, "context": context})
                            
                            if isinstance(response, dict):
                                clean_answer = response.get("output") or response.get("answer") or str(response)
                            else:
                                clean_answer = str(response)
                            
                            clean_answer = clean_text(clean_answer.strip())
                            print("DEBUG: Method 2 (manual retrieval) succeeded!")
                        else:
                            raise Exception("Retriever or LLM not available")
                    except Exception as e2:
                        print(f"DEBUG: Method 2 failed: {e2}")
                        clean_answer = f"Error generating answer: {e2}"
                
                print(f"Answer: {clean_answer}")
                print("--------------------------------------------------\n\n")
                
                # Store current Q&A for real-time display WITH CLEANED TEXT
                jobs[job_id]["current_qa"] = {
                    "index": i + 1,
                    "question": clean_question,
                    "answer": clean_answer
                }
                
                # Write to CSV with numbering and CLEANED TEXT
                csv_writer.writerow([i + 1, clean_question, clean_answer])

        # Final update
        jobs[job_id]["status"] = "done"
        jobs[job_id]["file"] = output_file
        jobs[job_id]["progress"] = 100
        jobs[job_id]["current_qa"] = None  # Clear current Q&A
        
        print(f"CSV generated successfully: {output_file}")

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        print(f"Error generating CSV: {e}")
        import traceback
        traceback.print_exc()  # This will print the full traceback

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
    
    # Extract original filename from the pdf_filename path
    original_filename = os.path.basename(pdf_filename)
    
    # Initialize job with progress tracking
    jobs[job_id] = {
        "status": "queued", 
        "file": None,
        "progress": 0,
        "total_questions": 0,
        "current_question": 0,
        "current_qa": None
    }
    
    # Add background task with original filename
    background_tasks.add_task(generate_csv, pdf_filename, job_id, original_filename)

    return Response(
        jsonable_encoder(json.dumps({"job_id": job_id, "status": jobs[job_id]["status"]}))
    )

@app.get("/status/{job_id}")
async def job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
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
        
        # Also include the professional filename for download
        professional_name = os.path.basename(job["file"])
        response_data["download_filename"] = professional_name
    
    return Response(jsonable_encoder(json.dumps(response_data)))

# ───────────────────────────────────────────────
# Run Server
# ───────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("app:app", host='127.0.0.1', port=8080, reload=False)