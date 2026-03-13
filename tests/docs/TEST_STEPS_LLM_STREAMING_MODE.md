## LLM Streaming Mode Test Steps

1. Start backend and Android app with a valid test account.
2. Open **Me → Settings** and enable **LLM streaming mode**.
3. Send a chat message and verify assistant text appears incrementally (first token arrives before full reply).
4. Disable **LLM streaming mode** in **Me → Settings**.
5. Send another chat message and verify assistant text appears only after full response returns.
6. Confirm both modes still save final assistant messages correctly in chat history.
