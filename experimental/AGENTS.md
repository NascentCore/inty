# AGENTS.md · experimental/（原型与实验）

- 非生产代码；
- 最小化依赖、隔离环境；如需脚本/服务，请在本目录自备 `requirements.txt` 或说明。
- requirements.txt 不指定版本，默认最新版本，使用以下步骤强制安装最新版本
  ```bash
  uv pip uninstall -r requirements.txt
  uv pip install -r requirements.txt
  ```
- 使用 https://pypi.org/project/python-dotenv/ 来读取环境变量来获得 API Key
  ```python
  from dotenv import load_dotenv
  load_dotenv()
  ```
