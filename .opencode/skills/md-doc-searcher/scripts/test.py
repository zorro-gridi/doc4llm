import os
import dotenv
dotenv.load_dotenv('.claude/.env')

from huggingface_hub import InferenceClient


MODEL_ID = 'BAAI/bge-large-en-v1.5'
# MODEL_ID = 'BAAI/bge-large-zh-v1.5'


import numpy as np
from huggingface_hub import InferenceClient


# ========== 初始化客户端 ==========
client = InferenceClient(
    provider="hf-inference",
    api_key=os.environ["HF_KEY"],
)

# ========== Embedding 函数 ==========
def embed_texts(texts):
    """
    texts: List[str]
    return: np.ndarray [N, D]
    """
    outputs = client.feature_extraction(
        texts,
        model=MODEL_ID,
    )
    return np.array(outputs, dtype=np.float32)

# ========== 向量归一化 ==========
def normalize(v):
    return v / np.linalg.norm(v, axis=1, keepdims=True)

# ========== Demo ==========
if __name__ == "__main__":
    # query = "苹果发布了新款 iPhone"

    # corpus = [
    #     "苹果公司发布了新手机",
    #     "今天北京下雨了",
    #     "Apple released a new iPhone",
    #     "微软推出了新的 Copilot 功能",
    #     "特斯拉发布了新款电动车",
    # ]

    query = 'Agent Skills'
    # query = 'GitHub'

    corpus = [
        "skills creation guide",
        "skills setup tutorial",
        "how to create skills in",
        "skills configuration reference",
        "skills creating"
    ]
    corpus.append(' '.join(corpus))

    # 1. 算 embedding
    q_emb = embed_texts([query])        # [1, D]
    c_embs = embed_texts(corpus)        # [N, D]

    # 2. normalize（用于 cosine / dot product）
    q_emb = normalize(q_emb)
    c_embs = normalize(c_embs)

    # 3. 相似度计算（cosine = dot）
    scores = q_emb @ c_embs.T           # [1, N]

    # 4. 排序
    reranked = sorted(
        zip(corpus, scores[0]),
        key=lambda x: x[1],
        reverse=True
    )

    # 5. 输出结果
    print("Query:", query)
    print("\nRerank Results:")
    for text, score in reranked:
        print(f"{score:.4f} | {text}")
