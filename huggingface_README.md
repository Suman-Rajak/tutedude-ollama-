---
title: DocuMind AI Document Assistant
emoji: 📄
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 8501
tags:
  - streamlit
  - langchain
  - groq
pinned: false
short_description: Summarize documents and ask questions with Groq + LangChain
---

# 📄 DocuMind - AI Document Assistant

Upload a PDF or text file (or use the sample), get a summary and ask questions about it.

- **LLM:** Groq (`openai/gpt-oss-120b`) through LangChain
- **Retrieval:** BM25 keyword search over the document chunks
- **UI:** Streamlit, running in Docker on Hugging Face Spaces

Built by Suman Rajak for my GenAI course (Assignment 39).
