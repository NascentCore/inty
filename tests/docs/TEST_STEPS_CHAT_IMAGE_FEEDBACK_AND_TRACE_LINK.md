# Chat image feedback + trace link test steps

1. Start Postgres:  
   `docker run --rm --name pg-inty -p 5432:5432 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD='sxwl666!' -e POSTGRES_DB=inty -d postgres:16`
2. Apply migrations:  
   `source .venv/bin/activate && PYTHONPATH=. alembic -c alembic/alembic.ini upgrade head`
3. Start backend:  
   `source .venv/bin/activate && ./backend/inty/start.sh --test`
4. Build/sync evaluation static assets:  
   `./evaluation/build.sh`
5. Start ops backend (serves evaluation):  
   `./backend/ops/start.sh --local`
6. Open `http://localhost:8001`, go to `单角色聊天`, trigger image thumbs feedback, submit feedback form.
7. Go to `生成图片管理` and verify generated image detail shows:
   - LangSmith trace link
   - saved image feedback entry
