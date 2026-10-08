"""
DocuMind - AI Document Assistant (my GenAI app for Assignment 39)
Upload a PDF or text file (or use the sample), get a summary, and ask questions about it.
LLM: Groq (free API key) through LangChain. Retrieval: BM25 keyword search (no heavy embedding model,
so the app stays small and starts fast on free hosting).

Run locally:  streamlit run app.py
Deployed on:  Streamlit Community Cloud and Hugging Face Spaces (Docker + Streamlit)
"""
import io
import os
import re

import streamlit as st
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PDF = os.path.join(APP_DIR, "data", "sahyadri_library_annual_report.pdf")
DEFAULT_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
IDK = "I couldn't find this in the document."
SHORT_DOC_CHARS = 12000          # up to this size the whole document goes into one prompt

st.set_page_config(page_title="DocuMind - AI Document Assistant", page_icon="📄", layout="wide")


# ======================= API key (works locally, on Streamlit Cloud and on HF Spaces) =======================
def configured_key() -> str:
    """Streamlit Cloud: Secrets (st.secrets). HF Spaces: Secrets (environment variables). Locally: .env."""
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("GROQ_API_KEY", "")
        except Exception:                  # no secrets file at all
            key = ""
    if not key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            key = os.getenv("GROQ_API_KEY", "")
        except ImportError:
            pass
    return "" if key.strip().startswith("paste") else key.strip()


@st.cache_data(ttl=3600, show_spinner=False)
def available_models(api_key: str):
    """Ask Groq which chat models exist (Groq retires models from time to time)."""
    try:
        from groq import Groq
        ids = sorted(m.id for m in Groq(api_key=api_key).models.list().data)
        skip = ("whisper", "guard", "tts", "orpheus", "playai", "distil", "prompt", "compound")
        chat = [i for i in ids if not any(s in i.lower() for s in skip)]
        preferred = [m for m in DEFAULT_MODELS if m in chat]
        return preferred + [m for m in chat if m not in preferred] or DEFAULT_MODELS
    except Exception:
        return DEFAULT_MODELS


def get_llm(api_key: str, model: str):
    from langchain_groq import ChatGroq
    extra = {"reasoning_effort": "low"} if "gpt-oss" in model else {}
    return ChatGroq(model=model, api_key=api_key, temperature=0.2, max_retries=4, **extra)


def friendly_error(e: Exception) -> str:
    text, name = str(e), type(e).__name__
    if "401" in text or "invalid_api_key" in text or "Authentication" in name:
        return "The Groq API key was rejected. Check the key in the app's secrets (or the sidebar)."
    if "429" in text or "rate_limit" in text or "RateLimit" in name:
        return "Groq's free limit was reached. Please wait a minute and try again."
    if "413" in text or "too large" in text.lower():
        return "This request was too large for the free Groq limit. Try a shorter document."
    return f"Something went wrong: {name}: {text[:200]}"


# ======================= document handling =======================
def read_document(name: str, data: bytes) -> str:
    if name.lower().endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(f"[page {i + 1}]\n{(p.extract_text() or '').strip()}" for i, p in enumerate(reader.pages))
    return data.decode("utf-8", errors="ignore")


def split_text(text: str, size: int = 2000, overlap: int = 200):
    return RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap).split_text(text)


def tokenize(text: str):
    return re.findall(r"[a-z0-9]+", text.lower())


def retrieve(question: str, chunks, k: int = 4):
    """BM25 keyword search: finds the chunks that share the most (rare) words with the question."""
    from rank_bm25 import BM25Okapi
    bm25 = BM25Okapi([tokenize(c) for c in chunks])
    scores = bm25.get_scores(tokenize(question))
    ranked = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
    return [chunks[i] for i in ranked[:k]]


# ======================= prompts =======================
STYLES = {
    "Short summary (5-6 lines)": "a short summary of 5-6 lines",
    "Bullet points": "6-10 bullet points, one line each, starting with '- '",
    "Detailed summary": "a detailed summary with a short heading for each main topic",
}
SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an expert summarizer. Summarize only what is in the text. Keep important numbers, names "
               "and dates. Do not add anything that is not in the text."),
    ("human", "Write {style} of this document:\n\n{text}"),
])
MAP_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Summarize this part of a longer document in 4-6 sentences. Keep important numbers, names and dates."),
    ("human", "{text}"),
])
QA_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Answer the question using ONLY the document excerpts below. "
               f"If the answer is not in them, reply exactly: \"{IDK}\" "
               "Keep the answer short and mention the page number if it is shown, like (page 3).\n\n"
               "Document excerpts:\n{context}"),
    ("human", "{question}"),
])


def summarize(llm, text: str, style: str):
    """Short documents: one call with the whole text (stuff). Long documents: map-reduce."""
    chain = SUMMARY_PROMPT | llm | StrOutputParser()
    if len(text) <= SHORT_DOC_CHARS:
        return chain.invoke({"style": STYLES[style], "text": text}), "stuff (1 call)"
    parts = split_text(text, size=6000, overlap=300)
    part_summaries = (MAP_PROMPT | llm | StrOutputParser()).batch([{"text": p} for p in parts], config={"max_concurrency": 2})
    combined = "\n\n".join(part_summaries)
    return chain.invoke({"style": STYLES[style], "text": combined}), f"map-reduce ({len(parts)} parts + 1 combine call)"


# ======================= UI =======================
st.title("📄 DocuMind - AI Document Assistant")
st.caption("Upload a PDF or text file, get a summary in seconds and ask questions about it. "
           "Powered by Groq + LangChain. Built by Suman Rajak.")

for key, value in {"doc_name": None, "doc_text": "", "chunks": [], "chat": [], "summary": None}.items():
    if key not in st.session_state:
        st.session_state[key] = value

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = configured_key()
    if api_key:
        st.success("Groq API key loaded from the app's secrets ✅")
    own_key = st.text_input("Use your own Groq API key (optional)", type="password",
                            help="Free key: https://console.groq.com/keys - it's only used in your session.")
    api_key = own_key.strip() or api_key
    if not api_key:
        st.warning("No Groq API key found. Add GROQ_API_KEY to the app's secrets, or paste your own key above.")
    model = st.selectbox("Model", available_models(api_key) if api_key else DEFAULT_MODELS)

    st.header("📁 Document")
    source = st.radio("Choose a document", ["Use the sample document", "Upload a file", "Paste text"])
    new_doc = None
    if source == "Use the sample document":
        st.caption("Sample: annual report of a made-up library in Pune (8 pages).")
        if st.button("Load sample"):
            with open(SAMPLE_PDF, "rb") as f:
                new_doc = ("sahyadri_library_annual_report.pdf", f.read())
    elif source == "Upload a file":
        upload = st.file_uploader("PDF, TXT or MD (max 5 MB)", type=["pdf", "txt", "md"])
        if upload is not None and upload.name != st.session_state.doc_name:
            if upload.size > 5 * 1024 * 1024:
                st.error("This file is larger than 5 MB.")
            else:
                new_doc = (upload.name, upload.getvalue())
    else:
        pasted = st.text_area("Paste your text here", height=150)
        if st.button("Use this text") and pasted.strip():
            new_doc = ("pasted text", pasted.encode("utf-8"))

    if new_doc:
        try:
            text = read_document(*new_doc)
        except Exception as e:
            st.error(f"Couldn't read the file: {type(e).__name__}")
            text = ""
        if len(re.sub(r"\[page \d+\]|\s", "", text)) < 50:
            st.error("No readable text found. The text is too short, or the PDF is scanned (images only).")
        else:
            st.session_state.update(doc_name=new_doc[0], doc_text=text, chunks=split_text(text), chat=[], summary=None)

    if st.session_state.doc_name:
        st.info(f"**Loaded:** {st.session_state.doc_name}  \n"
                f"{len(st.session_state.doc_text):,} characters · {len(st.session_state.chunks)} chunks")

if not st.session_state.doc_name:
    st.info("👈 Load the sample document, upload a file or paste some text to start.")
    st.stop()

tab_summary, tab_chat, tab_text = st.tabs(["📝 Summarize", "💬 Ask questions", "📄 Document text"])

with tab_summary:
    style = st.radio("Summary style", list(STYLES), horizontal=True)
    if st.button("Summarize", type="primary", disabled=not api_key):
        try:
            with st.spinner("Summarizing..."):
                summary, method = summarize(get_llm(api_key, model), st.session_state.doc_text, style)
            st.session_state.summary = (style, summary, method)
        except Exception as e:
            st.error(friendly_error(e))
    if st.session_state.summary:
        style_used, summary, method = st.session_state.summary
        st.markdown(f"#### {style_used}")
        st.markdown(summary)
        st.caption(f"Method: {method} · model: {model}")
        st.download_button("Download summary", summary, file_name="summary.txt")

with tab_chat:
    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    if question := st.chat_input("Ask a question about the document...", disabled=not api_key):
        st.session_state.chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            try:
                with st.spinner("Searching the document..."):
                    excerpts = retrieve(question, st.session_state.chunks)
                    answer = (QA_PROMPT | get_llm(api_key, model) | StrOutputParser()).invoke(
                        {"context": "\n\n---\n\n".join(excerpts), "question": question})
                st.markdown(answer)
                with st.expander("Document excerpts used"):
                    for ex in excerpts:
                        st.text(ex[:600] + ("..." if len(ex) > 600 else ""))
            except Exception as e:
                answer = "⚠️ " + friendly_error(e)
                st.error(answer)
        st.session_state.chat.append({"role": "assistant", "content": answer})
    if st.session_state.chat and st.button("Clear chat"):
        st.session_state.chat = []
        st.rerun()

with tab_text:
    st.text_area("Extracted text", st.session_state.doc_text, height=400, disabled=True)
