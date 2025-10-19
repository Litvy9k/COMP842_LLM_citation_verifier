# from huggingface_hub import snapshot_download

# model_id = "mistralai/Mistral-7B-Instruct-v0.3"
# target_dir = "model"

# local_path = snapshot_download(
#     repo_id=model_id,
#     cache_dir=target_dir,
#     local_dir=target_dir,
#     local_dir_use_symlinks=False
# )

# from sentence_transformers import SentenceTransformer

# model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
# model.save("model/all-MiniLM-L6-v2")

from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-small-en-v1.5")
model.save("model/bge-small-en-v1.5")