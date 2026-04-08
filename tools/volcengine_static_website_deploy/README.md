# Volcengine TOS static website deploy

Small helper to upload selected files from a local directory to [Volcengine TOS](https://www.volcengine.com/docs/6349/655980) with `public-read`, then call `PutBucketWebsite` (default index), matching the console flow in [设置静态网站](https://www.volcengine.com/docs/6349/114714?lang=zh).

## Setup

```bash
cd tools/volcengine_static_website_deploy
pip install -r requirements.txt
```

## Credentials

Set either pair:

- `VOLC_ACCESSKEY` and `VOLC_SECRET_ACCESSKEY`, or
- `TOS_ACCESS_KEY` and `TOS_SECRET_KEY`

Also set `TOS_BUCKET` or pass `--bucket`. Optional: `TOS_REGION`, `TOS_ENDPOINT`, `TOS_WEBSITE_ERROR_KEY` (404 object key if you upload that file).

## Example: Vertex Gemini pricing page

From repo root, after building the static assets:

```bash
cd tools/vertex-gemini-pricing && yarn install && yarn build && cd ../volcengine_static_website_deploy
export VOLC_ACCESSKEY=... VOLC_SECRET_ACCESSKEY=... TOS_BUCKET=your-bucket TOS_REGION=cn-beijing
python deploy.py ../vertex-gemini-pricing index.html dist/app.js src/styles.css
```

## Usage

```text
python deploy.py SITE_ROOT REL_PATH [REL_PATH ...] [--bucket NAME] [--region REGION]
  [--endpoint URL] [--create-bucket] [--skip-website-config] [--index-suffix index.html]
```

`SITE_ROOT` is the local document root. Each `REL_PATH` is uploaded under the same key in the bucket (e.g. `dist/app.js` stays `dist/app.js`).
