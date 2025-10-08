from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch, os

app = FastAPI()

model_path = os.path.expanduser("~/git_workspace/COMP842_LLM_citation_verifier/model/mistral-7b")
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    device_map="auto",
    torch_dtype=torch.float16
)

class Query(BaseModel):
    prompt: str
    max_tokens: int = 100

@app.post("/generate")
async def generate_text(query: Query):
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Answer concisely and stop when done."},
        {"role": "user", "content": query.prompt}
    ]
    prompt_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=query.max_tokens,
        temperature=0.3,
        top_p=0.9,
        do_sample=True,
        eos_token_id=tokenizer.eos_token_id,
    )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    if "assistant" in response.lower():
        response = response.split("assistant")[-1].strip()

    return {"response": response}