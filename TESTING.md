# Testing checklist

## Automated (no model needed)
```
python selftest.py      # 40 checks: login, per-user history, FAQ evidence, page labels, prompt, answer flow
python verify_faq.py    # every FAQ sentence is found on the stated PDF page
```
Both passed when this package was built. They do not test the Streamlit screens or the real model.

## Manual checklist (tick each after running `streamlit run app.py`)
**Login**
- [ ] Wrong password shows an error; five wrong tries lock the form for 60 seconds.
- [ ] Empty fields show a warning. Show/hide eye on the password field works.
- [ ] Student and employee demo accounts log in. Forgot Password shows the notice. Remember Me fills the number next visit.

**Chatbot**
- [ ] First question shows the start-up status, then an answer with a Sources expander.
- [ ] Click a suggested question: it is asked. Ask a follow-up ("what about faculty?") and check it uses the context.
- [ ] "What is the retirement age?" gives 60 and cites Faculty Handbook page 37. "How many tardy marks equal one absence?" gives three, page 13.
- [ ] "What are the library opening hours?" gives the standard "couldn't find sufficient information" reply.
- [ ] A question over 500 characters is blocked. Empty input is ignored.
- [ ] New Chat and Clear Conversation work. "hello" gets a greeting without a model call.

**FAQ**
- [ ] Search filters entries; no match shows the empty state; "Ask this in the chatbot" opens the chatbot with the question.

**Documents**
- [ ] The combined PDF is listed with pages, size, status, and a working download.
- [ ] Student account sees the read-only note; employee account can rebuild the index.
- [ ] Employee upload of a non-PDF, a renamed text file, and an encrypted PDF is rejected.

**History**
- [ ] Conversations appear after chatting; Open reloads one; Delete asks for confirmation and removes it.
- [ ] Log in as the other demo user: the first user's conversations are not visible.

**Settings and layout**
- [ ] Text size and expanded-sources preferences persist after logout and login. Log out works.
- [ ] Layout is usable at phone width (narrow the browser) and on a tablet.
- [ ] Stop the app, delete `chroma_db/manifest.json`, restart: the index rebuilds once, then is reused.

**First-question check (needs the real models)**
1. `python prepare.py` finishes and prints a test answer with timings.
2. `python benchmark.py` prints load time and per-stage times.
3. `streamlit run app.py`, log in: the Chat page shows "Starting the chatbot (n s)" and then "Chatbot online".
4. Ask a question, then a second and a third: the second and third start streaming immediately (no reload).
5. Ask something not in the handbooks (e.g. capital of France): the standard refusal sentence appears.
6. Disconnect the network with models not cached: a clear error and a Retry button appear, never an endless spinner.
