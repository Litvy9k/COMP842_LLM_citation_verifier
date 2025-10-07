from transformers import AutoTokenizer, AutoModelForCausalLM

model_id = "mistralai/Mistral-7B-Instruct-v0.3"
tokenizer = AutoTokenizer.from_pretrained(model_id, token="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")
model = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto", torch_dtype="auto", token="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")