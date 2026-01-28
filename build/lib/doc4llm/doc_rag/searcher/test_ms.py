import os
import dotenv
dotenv.load_dotenv('doc4llm/.env')

from openai import OpenAI
import numpy as np


MODEL_ID = 'Qwen/Qwen3-Embedding-8B'


# ========== 初始化客户端 ==========
client = OpenAI(
    base_url='https://api-inference.modelscope.cn/v1',
    api_key=os.environ.get("MODELSCOPE_KEY"),  # ModelScope Token
)


# ========== Embedding 函数 ==========
def embed_texts(texts):
    """
    texts: List[str]
    return: np.ndarray [N, D]
    """
    response = client.embeddings.create(
        model=MODEL_ID,
        input=texts,
        encoding_format="float"
    )
    # 提取 embedding 向量
    embeddings = [data.embedding for data in response.data]
    return np.array(embeddings, dtype=np.float32)


# ========== 向量归一化 ==========
def normalize(v):
    return v / np.linalg.norm(v, axis=1, keepdims=True)


# ========== Demo ==========
if __name__ == "__main__":
    query = 'create rules'
    corpus = [
        'Create a plugin',
        'a plugin',
        'agents',
        'Create agents',
        'Rules'
    ]

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
