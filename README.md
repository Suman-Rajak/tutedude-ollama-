# GenAI-Task39-SumanRajak

## Assignment 39 - GenAI App Deployment

I deployed my GenAI app, **DocuMind - AI Document Assistant**, on two platforms: **Streamlit Community Cloud** and **Hugging Face Spaces**.

**Live links:**
- Streamlit Cloud: ADD-YOUR-STREAMLIT-URL-HERE
- Hugging Face Spaces: ADD-YOUR-HF-SPACE-URL-HERE
- GitHub repository: ADD-YOUR-GITHUB-REPO-URL-HERE

## The app

DocuMind lets anyone upload a PDF or text file (or use the sample document), get a summary and ask questions about it.

- **Summarize:** short summary, bullet points or a detailed summary. Short documents go to the LLM in one call (stuff). Long documents are split into parts that are summarized first and then combined (map-reduce)
- **Ask questions:** the app finds the most relevant parts of the document with BM25 keyword search, and the LLM answers only from them. If the answer isn't in the document, it says so
- **LLM:** Groq (`openai/gpt-oss-120b`, free API key) through LangChain. The model list comes from Groq, so a retired model can't break the app
- **Session state:** the loaded document, the chat and the last summary are kept in `st.session_state`

For deployment I kept the app small. It has no local models and no heavy libraries like PyTorch, so it installs in about a minute and runs well on the free hosting plans. I used BM25 keyword search instead of an embedding model for the same reason.

## Files in this folder

- `app.py` - the Streamlit app (one file, so it's easy to deploy)
- `requirements.txt` - the packages needed on both platforms
- `data/sahyadri_library_annual_report.pdf` - the sample document (a made-up library annual report)
- `.streamlit/config.toml` - theme and upload limit (5 MB)
- `.streamlit/secrets.toml.example` - shows the format of the secret. The real `secrets.toml` is never committed
- `Dockerfile` - for Hugging Face Spaces (Docker SDK with Streamlit, port 8501, user 1000)
- `huggingface_README.md` - the README with the YAML configuration that I used for the Hugging Face Space
- `.gitignore` - keeps `.env` and `secrets.toml` out of GitHub

## How I handled the API key

The Groq key is a secret, so it's never in the code or on GitHub. `app.py` looks for it in this order:
1. environment variables (Hugging Face Spaces turns its secrets into environment variables)
2. `st.secrets` (Streamlit Cloud's secrets)
3. a local `.env` file

Users can also paste their own free Groq key in the sidebar. That key is only used in their own session.

## Task 1 - How I deployed on Streamlit Cloud

1. **Pushed the project to GitHub.** I created a new public repository on GitHub, then ran this in the project folder:
   ```
   git init
   git add .
   git commit -m "DocuMind - AI document assistant"
   git branch -M main
   git remote add origin https://github.com/<my-username>/documind-ai.git
   git push -u origin main
   ```
   The repository contains `app.py` and `requirements.txt` at the top level. I checked on GitHub that no `.env` or `secrets.toml` was uploaded.
2. **Deployed:** on https://share.streamlit.io I signed in with GitHub and clicked **Create app** → **Deploy a public app from GitHub**, then chose:
   - Repository: `documind-ai`
   - Branch: `main`
   - Main file: `app.py`
   - App URL: my own subdomain
3. **Added the secret:** under **Advanced settings → Secrets** I pasted `GROQ_API_KEY = "my-key"` (TOML format) and chose Python 3.12. Then I clicked **Deploy**.
4. **Tested the live URL:** I waited for the build to finish, then loaded the sample, created all three summary types, asked questions, including one that's not in the document, and uploaded my own PDF. Every new push to `main` redeploys the app automatically.

## Task 2 - How I deployed on Hugging Face Spaces

1. **Created a new Space:** on https://huggingface.co/new-space I chose:
   - a name (`documind-ai`) and the license
   - **SDK: Docker → Streamlit template.** Hugging Face has deprecated the old built-in "Streamlit" SDK and now recommends Docker with the Streamlit template
   - hardware: **CPU basic** (free)
   - visibility: public
2. **Uploaded the files:** in the Space's **Files** tab I used **Add file → Upload files** to upload `app.py`, `requirements.txt`, `Dockerfile` and the `data/` folder, replacing the template's files. (Instead of uploading, I could also push with git to the Space's own repository, `git clone https://huggingface.co/spaces/<user>/documind-ai`.)
3. **Configured README.md:** I replaced the Space's README with the content of `huggingface_README.md`. Its YAML header sets:
   - the title, emoji and colours
   - `sdk: docker`
   - `app_port: 8501` (the only port Streamlit Spaces allow)
   - tags and a short description
4. **Added the secret:** in **Settings → Variables and secrets** I added a **secret** called `GROQ_API_KEY`, which the container receives as an environment variable.
5. **Deployed and tested:** the Space built the Docker image (the **Logs** tab shows the build) and started the app. I ran the same tests as on Streamlit Cloud.

## Task 3 - Comparing the deployment platforms

**1. Streamlit Cloud vs Hugging Face Spaces**

| | Streamlit Community Cloud | Hugging Face Spaces |
|---|---|---|
| Made for | Streamlit apps only | ML demos: Gradio, Docker (incl. Streamlit) and static sites |
| Source of the code | a GitHub repository (required) | its own git repository: upload in the browser, git push, or sync from GitHub with an Action |
| Setup | very simple: choose repo, branch and file | a bit more: choose the SDK, a Dockerfile for Streamlit, README YAML config |
| Secrets | TOML in the app settings, read with `st.secrets` | Settings → secrets, read as environment variables |
| Free hardware | shared CPU with limited memory | CPU basic for free; paid upgrades to bigger CPUs and GPUs |
| Updates | automatic on every push to GitHub | automatic on every commit to the Space |
| Sleeping | sleeps after some days without visitors, wakes up when opened | free Spaces sleep after a period of inactivity |
| Community | Streamlit gallery | Hugging Face Hub: likes, discoverability, next to models and datasets |

**2. Pros & cons**

*Streamlit Cloud*
- ✅ the fastest and easiest way to deploy a Streamlit app, and it's free
- ✅ GitHub integration, automatic redeploys and simple secrets
- ❌ only Streamlit apps
- ❌ limited free resources, no GPUs, so it's not suited for running models locally
- ❌ the code has to be on GitHub

*Hugging Face Spaces*
- ✅ supports many frameworks and full Docker, so you control the environment
- ✅ GPU hardware is available (paid), which suits apps that run open-source models
- ✅ the app sits next to models and datasets on the Hub, which is good for sharing ML work
- ❌ more setup for Streamlit (Docker, port, README config) and slower builds
- ❌ free Spaces sleep after inactivity, and the first visit after that is slow

**3. When to use which**
- **Streamlit Cloud:** for a Streamlit app that calls an API (like my app with Groq), quick demos, dashboards and internal tools, where the code is already on GitHub and I want the simplest deployment.
- **Hugging Face Spaces:** when the app runs an open-source model itself and needs more memory or a GPU, when I need Docker or another framework (Gradio), or when I want to share the demo with the ML community on the Hub.

For DocuMind both work well, because the heavy work happens at Groq. If I changed it to run a local Hugging Face model, Spaces would be the better choice.

## How I ran it locally first

```
pip install -r requirements.txt
streamlit run app.py
```
I put my Groq key in a local `.env` file (`GROQ_API_KEY=...`) or in `.streamlit/secrets.toml`. Neither file is included in this folder or on GitHub.
