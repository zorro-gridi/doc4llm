from dotenv import load_dotenv
load_dotenv('doc4llm/.env')

from sentence_transformers import SentenceTransformer
from transformers import logging

# 禁用加载模型时的进度条（如下载权重时的进度条）
logging.disable_progress_bar()
# 只显示 error，不显示 info / warning
logging.set_verbosity_error()


import os

from huggingface_hub import login
login(token=os.environ['HF_KEY'])

# os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
# os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"

# from huggingface_hub import snapshot_download
# snapshot_download("BAAI/bge-base-en-v1.5")


sentences_1 = ["transcript working mechanism"]
sentences_2 = [
    "Session quality surveys\nWhen you see the “How is Claude doing this session?” prompt in Claude Code, responding to this survey (including selecting “Dismiss”), only your numeric rating (1, 2, 3, or dismiss) is recorded. We do not collect or store any conversation transcripts, inputs, outputs, or other session data as part of this survey. Unlike thumbs up/down feedback or `/bug` reports, this session quality survey is a simple product satisfaction metric. Your responses to this survey do not impact your data training preferences and cannot be used to train our AI models.\n### Data retention",

    "\n\"session_id\": \"abc123\",\n\"transcript_path\": \"/Users/.../.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl\",\n\"cwd\": \"/Users/...\",\n\"permission_mode\": \"default\"",

    "2. **JSON with`additionalContext`** (structured): Use the JSON format below for more control. The `additionalContext` field is added as context.\nBoth methods work with exit code 0. Plain stdout is shown as hook output in the transcript; `additionalContext` is added more discretely. **Blocking prompts:**\n* `\"decision\": \"block\"` prevents the prompt from being processed. The submitted prompt is erased from context. `\"reason\"` is shown to the user but not added to context.",

    "* Standard: 30-day retention period\n* Zero data retention: Available with appropriately configured API keys - Claude Code will not retain chat transcripts on servers\n* Local caching: Claude Code clients may store sessions locally for up to 30 days to enable session resumption (configurable)",

    "### Development Partner Program\nIf you explicitly opt in to methods to provide us with materials to train on, such as via the [Development Partner Program](https://support.claude.com/en/articles/11174108-about-the-development-partner-program), we may use those materials provided to train our models. An organization admin can expressly opt-in to the Development Partner Program for their organization. Note that this program is available only for Anthropic first-party API, and not for Bedrock or Vertex users. If you choose to send us feedback about Claude Code using the `/bug` command, we may use your feedback to improve our products and services. Transcripts shared via `/bug` are retained for 5 years.\n### Session quality surveys",
    ]

model = SentenceTransformer('BAAI/bge-base-en-v1.5')
embeddings_1 = model.encode(sentences_1, normalize_embeddings=True)
embeddings_2 = model.encode(sentences_2, normalize_embeddings=True)
similarity = embeddings_1 @ embeddings_2.T
print(similarity)
