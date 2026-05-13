# Chat image feedback + trace link test steps

1. Start Postgres:  
   `docker run --rm --name pg-inty -p 5432:5432 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD='sxwl666!' -e POSTGRES_DB=inty -d postgres:16`
2. Apply migrations:  
   `source .venv/bin/activate && PYTHONPATH=. alembic -c backend/alembic/alembic.ini upgrade head`
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

## Android app manual regression (chat-to-image thumbs prompt)

1. Open chat with an iMate and generate an image from a message.
2. Tap 👍 or 👎 below the generated image preview.
3. Verify the feedback request popup appears on first thumbs action of the local day.
4. Tap **Send Suggestions** and verify Feedback page opens with:
   - the generated image prefilled in evidence list
   - image-quality reason options (`IMAGE_LOW_QUALITY`, `IMAGE_STYLE_MISMATCH`, `IMAGE_CONTENT_MISMATCH`, `IMAGE_ANATOMY_OR_STRUCTURE_ERROR`, `IMAGE_OTHER`)
5. Submit feedback and verify in ops `举报与反馈` page:
   - `report_type = FEEDBACK`
   - `target_id` starts with `IMAGE_FEEDBACK_`
   - `description` starts with `[IMAGE_FEEDBACK][vote=like|dislike]`
   - `image_urls` contains the generated image URL
6. Repeat thumbs action on the same local day and verify popup does not show again.
