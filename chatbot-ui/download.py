from huggingface_hub import snapshot_download

model_id = "mistralai/Mistral-7B-Instruct-v0.3"
target_dir = "model"

local_path = snapshot_download(
    repo_id=model_id,
    cache_dir=target_dir,
    local_dir=target_dir,
    local_dir_use_symlinks=False
)