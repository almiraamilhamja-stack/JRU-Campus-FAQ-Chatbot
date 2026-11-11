# Deployment notes (localhost first)

**Localhost (recommended for the demo):** follow README.md. Keep the app on localhost or a private network.

**Sharing on a school network or a server (later):**
1. Use a machine with at least 8 GB RAM (16 GB comfortable on a CPU) or a GPU with 6 GB or more.
2. Run behind HTTPS (a reverse proxy such as Nginx or Caddy) and do not expose port 8501 directly to the internet.
3. Replace the demo accounts in `auth.py` with a real, approved identity system before real use. The demo accounts
   are test accounts only and must not be used to protect real data.
4. Keep `storage/` and `chroma_db/` on persistent disk and back them up. Set `JRU_DB_PATH` if you move the database.
5. Pre-download the models on the server (`huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct` and the embedding
   model) so the first question is fast, and build the index once with the Documents page.
6. Streamlit Community Cloud's free tier has too little memory for this model. Use your own server or a GPU host.
7. Run with `streamlit run app.py --server.port 8501`. Secrets, if you add any, belong in environment variables.
