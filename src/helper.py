# helper.py (corrected & production-ready)
from dotenv import load_dotenv
import os
import re
import time
from src.prompt import *   # prompt_template, refine_template, ANSWER_PROMPT expected here

# LangChain / Google GenAI imports
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import TokenTextSplitter
from langchain_core.documents import Document

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

from langchain_core.prompts import PromptTemplate
from langchain_classic.chains.summarize import load_summarize_chain
from langchain_classic.chains import RetrievalQA
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain

# Ensure environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not found in environment. Set it in .env.")
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY


def file_preprocessing(file_path):
    """
    Load PDF, produce two sets of documents:
      - docs_ques_gen : large chunks used for question-generation stage
      - docs_ans_gen  : smaller chunks used for retrieval / answer generation

    Returns:
        docs_ques_gen (List[Document]), docs_ans_gen (List[Document])
    """

    # Load data from PDF
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    # Concatenate pages into a single large text for question generation
    question_gen = ""
    for page in pages:
        question_gen += page.page_content + "\n"

    # Split into large chunks for question generation (preserve context)
    splitter_ques_gen = TokenTextSplitter(
        encoding_name="cl100k_base",
        chunk_size=10000,
        chunk_overlap=200
    )
    chunk_ques_gen = splitter_ques_gen.split_text(question_gen)
    docs_ques_gen = [Document(page_content=t) for t in chunk_ques_gen]

    # Split into smaller chunks for retrieval/answering
    splitter_ans_gen = TokenTextSplitter(
        encoding_name="cl100k_base",
        chunk_size=2000,
        chunk_overlap=200
    )
    docs_ans_gen = splitter_ans_gen.split_documents(docs_ques_gen)

    return docs_ques_gen, docs_ans_gen


def llm_pipeline(file_path):
    """
    Full pipeline:
      - preprocess file -> docs_ques_gen, docs_ans_gen
      - question generation chain (refine) -> ques (string with questions)
      - build embeddings + FAISS
      - prepare answer LLM and retrieval chain
      - filter & normalize generated questions
      - returns: ans_gen_chain (retrieval chain ready to invoke), filtered_questions (list)
    """

    #  File preprocessing
    docs_ques_gen, docs_ans_gen = file_preprocessing(file_path)

    #  LLM for question generation (Google Gemini)
    llm_ques_gen_pipeline = ChatGoogleGenerativeAI(
        temperature=0.3,
        model="gemini-2.5-flash"
    )

    # Prompts based on your src.prompt (expected variables imported above)
    PROMPT_QUESTIONS = PromptTemplate(template=prompt_template, input_variables=["text"])
    REFINE_PROMPT_QUESTIONS = PromptTemplate(
        input_variables=["existing_answer", "text"],
        template=refine_template
    )

    #  Build question-generation chain (refine)
    ques_gen_chain = load_summarize_chain(
        llm=llm_ques_gen_pipeline,
        chain_type="refine",
        verbose=True,
        question_prompt=PROMPT_QUESTIONS,
        refine_prompt=REFINE_PROMPT_QUESTIONS,
        # these names help the refine chain know which variable is which
        document_variable_name="text",
        initial_response_name="existing_answer",
    )

    # Run the question generation on the larger chunks
    ques = ques_gen_chain.run(docs_ques_gen)  # expects list[Document] or list[str]

    #  Embeddings + FAISS vector store (Google embeddings)
    embeddings = GoogleGenerativeAIEmbeddings(model="text-embedding-004")
    vector_store = FAISS.from_documents(docs_ans_gen, embeddings)

    #  LLM for answer generation (Google Gemini)
    llm_answer_gen = ChatGoogleGenerativeAI(
        temperature=0.1,
        model="gemini-2.5-flash"
    )

    ANSWER_PROMPT = PromptTemplate.from_template(
    """You are an expert on UN Sustainable Development Goals (SDGs).
    Your task is to extract and summarize the answer to the question using ONLY the provided CONTEXT.

    **RULES:**
    1.  **Strict Context Reliance:** Use ONLY the provided CONTEXT. Do NOT invent facts or generalize.
    2.  **Focus:** Directly extract the specific requirement or characteristic requested by the question from the relevant SDG Target in the context.
    3.  **No Citation:** Do NOT include 'Target X.Y', 'Goal X', or any reference/citation in the final answer.
    4.  **Failure State:** If the exact answer is not present in the context, reply exactly: **Not found in context.**
    5.  **Conciseness:** Provide a brief and precise answer, avoiding unnecessary elaboration.
    6.  **No Markdown:** Do NOT use any markdown formatting like *, **, `, or _ in your response.
    7.  **Plain Text Only:** Use only plain text with proper punctuation.
    8.  **Failure State:** If the exact answer is not present in the context, reply exactly: **Not found in context.**

    Context: {context}

    Question: {input}

    Answer in format: [Directly extracted answer/summary]."""
    )

    # Build retriever (MMR settings required)
    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 6, "fetch_k": 30, "lambda_mult": 0.5}
    )

    # Build combine_chain and retrieval chain (create once)
    combine_chain = create_stuff_documents_chain(llm_answer_gen, ANSWER_PROMPT)
    ans_gen_chain = create_retrieval_chain(retriever=retriever, combine_docs_chain=combine_chain)
    

    def clean_question_text(text):
        """Remove markdown formatting and special characters from questions"""
        if not isinstance(text, str):
            text = str(text)
        
        # Remove numbering like "1.", "2." etc.
        text = re.sub(r'^\s*\d+\.\s*', '', text)
        
        # Remove markdown formatting: *, **, `, etc.
        text = re.sub(r'[\*\_\`]', '', text)
        
        # Remove quotes that wrap content
        text = re.sub(r'^\"(.*)\"$', r'\1', text)
        text = re.sub(r"^\'(.*)\'$", r'\1', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Ensure it starts with capital letter
        if text and len(text) > 1:
            text = text[0].upper() + text[1:]
        
        return text


    ques_list = ques.split("\n")
    numbering_pattern = re.compile(r'^\s*\d+\.\s*')
    question_start_regex = re.compile(
        r'^(what|which|when|how|why|where|who|explain|describe|list|define)\b',
        re.I
    )

    filtered_questions = []
    seen = set()

    for raw in ques_list:
        q = raw.strip()
        if not q:
            continue

        # Remove numbering like "1." and bullet markers
        # q = numbering_pattern.sub('', q)
        q = clean_question_text(q)

        # Drop obvious headers/meta
        if len(q) < 5:
            continue
        low = q.lower()
        if low.startswith("here are") or low.startswith("the following"):
            continue

        # Ensure interrogative — allow short command-like prompts (e.g., "List three targets")
        if not (q.endswith('?') or question_start_regex.search(q)):
            continue

        # Normalize and dedupe
        q_norm = re.sub(r'\s+', ' ', q.strip()).lower()
        if q_norm in seen:
            continue
        seen.add(q_norm)

        # Standardize to end with '?'
        if not q.endswith('?'):
            q = q.rstrip('.') + '?'

        filtered_questions.append(q)

        # #  LIMIT TO 30 QUESTIONS MAXIMUM
        # if len(filtered_questions) >= 30:
        #     print(f"DEBUG: Limited to first 30 questions for faster processing")
        #     break

    # Return the prepared chain and filtered questions (for loop usage)
    return ans_gen_chain, filtered_questions, retriever, llm_answer_gen


def answer_questions_and_write(ans_gen_chain, filtered_questions, retriever, llm_answer_gen, answers_file="answers.txt"):
    """
    Given a prepared ans_gen_chain and filtered_questions, iterate, retrieve,
    summarize retrieved docs, then feed summarized_context to the combine chain
    (via the ans_gen_chain). Streaming attempted first; fallback to normal invoke.
    Saves answers to answers_file.
    """

    # Clear previous file
    open(answers_file, "w", encoding="utf-8").close()

    # Prepare a summarization chain (refine) to always produce summarized_context
    summarize_chain = load_summarize_chain(
        llm=llm_answer_gen,
        chain_type="refine",
        verbose=False
    )

    # If ans_gen_chain is a create_retrieval_chain instance, the combine part expects a 'context' that can be
    # either a string or the documents — we will provide summarized_context as a string.
    for idx, question in enumerate(filtered_questions, 1):
        print("=" * 60)
        print(f"Question {idx}: {question}")
        print("=" * 60)

        # Retrieve using MMR retriever (already configured)
        try:
            retrieved_docs = retriever.invoke(question)
        except Exception:
            # Fallback if .invoke not supported in this LangChain version
            try:
                retrieved_docs = retriever.get_relevant_documents(question)
            except Exception as e:
                retrieved_docs = []
                print(f"[Retriever error] {e}")

        # If nothing retrieved -> short-circuit
        if not retrieved_docs:
            answer_text = "Not found in context."
            print(f"Answer {idx}: {answer_text}\n")
            with open(answers_file, "a", encoding="utf-8") as f:
                f.write(f"Question {idx}: {question}\n")
                f.write(f"Answer {idx}: {answer_text}\n")
                f.write("-" * 60 + "\n\n")
            time.sleep(12)
            continue

        #  Summarize retrieved docs -> summarized_context (string)
        try:
            summarized_context = summarize_chain.run(retrieved_docs)
            # If summarization returns None or empty, fallback to concatenating page_content
            if not summarized_context or not summarized_context.strip():
                summarized_context = "\n\n".join([d.page_content for d in retrieved_docs])
        except Exception as e:
            print(f"[Summarization error] {e}")
            summarized_context = "\n\n".join([d.page_content for d in retrieved_docs])

        input_payload = {"input": question, "context": summarized_context}

        full_answer_text = ""
        try:
            # prefer streaming if available
            if hasattr(ans_gen_chain, "stream"):
                stream = ans_gen_chain.stream(input_payload)
                # Some stream implementations yield dict chunks; handle both
                for chunk in stream:
                    # chunk might be a dict with 'answer' or 'output' keys or a raw string
                    if isinstance(chunk, dict):
                        # look for likely fields
                        token = chunk.get("answer") or chunk.get("output") or chunk.get("text") or ""
                    else:
                        token = str(chunk)
                    full_answer_text += token
                    # Optionally print as it streams
                    print(token, end="", flush=True)
                print()  # final newline after stream
            else:
                response = ans_gen_chain.invoke(input_payload)
                # normalize possible shapes
                if isinstance(response, dict):
                    # typical fields: 'output' or 'answer' or 'result'
                    full_answer_text = response.get("output") or response.get("answer") or response.get("result") or str(response)
                else:
                    full_answer_text = str(response)
                print(f"Answer {idx}: {full_answer_text}")
        except Exception as e:
            # fallback: call combine chain directly (safe)
            try:
                combine_chain = create_stuff_documents_chain(llm_answer_gen, ANSWER_PROMPT)
                # combine_chain expects {"input": question, "context": summarized_context}
                result = combine_chain.invoke({"input": question, "context": summarized_context})
                if isinstance(result, dict):
                    full_answer_text = result.get("output") or result.get("answer") or str(result)
                else:
                    full_answer_text = str(result)
                print(full_answer_text)
            except Exception as e2:
                full_answer_text = f"[ERROR: {e}] / fallback error: {e2}"
                print(full_answer_text)

        # If strict format required but not found, produce natural-language summary as fallback
        if "Not found in context." in full_answer_text or not full_answer_text.strip():
            # Optional: try a more permissive answer: ask combine chain for a natural language summary
            try:
                combine_chain_nl = create_stuff_documents_chain(llm_answer_gen, PromptTemplate.from_template(
                    "Using only this context, provide a concise natural-language answer to the question.\n\nContext: {context}\n\nQuestion: {input}\n\nAnswer:"
                ))
                nl_result = combine_chain_nl.invoke({"input": question, "context": summarized_context})
                if isinstance(nl_result, dict):
                    nl_text = nl_result.get("output") or nl_result.get("answer") or str(nl_result)
                else:
                    nl_text = str(nl_result)
                # if model still returns nothing useful, keep "Not found in context."
                if nl_text and nl_text.strip():
                    full_answer_text = nl_text
            except Exception as e:
                # keep whatever we had
                pass

        # Persist to file
        with open(answers_file, "a", encoding="utf-8") as f:
            f.write(f"Question {idx}: {question}\n")
            f.write(f"Answer {idx}: {full_answer_text}\n")
            f.write("-" * 60 + "\n\n")

        # 7) Rate limit pause
        time.sleep(12)
