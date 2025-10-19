from typing import Any, List, Union
from transformers import AutoTokenizer, AutoModelForCausalLM
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.language_models import BaseLanguageModel
from langchain_core.outputs import Generation
from pydantic import PrivateAttr, ConfigDict
import torch, os

class LocalCausalLM(BaseLanguageModel):
    model_path: str
    max_tokens: int = 100

    _tokenizer: Any = PrivateAttr()
    _model: Any = PrivateAttr()

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_post_init(self, __context: Any) -> None:
        path = os.path.expanduser(self.model_path)
        self._tokenizer = AutoTokenizer.from_pretrained(path)
        self._model = AutoModelForCausalLM.from_pretrained(
            path,
            device_map="auto",
            dtype=torch.float16,
        )

    def _build_inputs(self, prompt_text: str):
        return self._tokenizer(prompt_text, return_tensors="pt", add_special_tokens=True)

    def invoke(self, prompt, config=None, **kwargs) -> str:
        from langchain_core.prompt_values import ChatPromptValue

        if isinstance(prompt, ChatPromptValue):
            prompt_text = prompt.to_string()
        else:
            prompt_text = str(prompt)

        inputs = self._tokenizer(prompt_text, return_tensors="pt", add_special_tokens=True)
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

        max_new_tokens = int(kwargs.get("max_tokens", self.max_tokens))
        gen_ids = self._model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            eos_token_id=self._tokenizer.eos_token_id,
            pad_token_id=self._tokenizer.eos_token_id,
        )

        input_len = inputs["input_ids"].shape[-1]
        new_tokens = gen_ids[0][input_len:]
        return self._tokenizer.decode(new_tokens, skip_special_tokens=True)

    def stream(self, prompt: Union[str, ChatPromptValue]):
        yield self.invoke(prompt)

    def batch(self, prompts: List[Union[str, ChatPromptValue]]) -> List[str]:
        return [self.invoke(p) for p in prompts]

    def bind(self, **kwargs):
        if "max_tokens" in kwargs:
            self.max_tokens = int(kwargs["max_tokens"])
        return self

    def predict(self, text: str) -> str:
        return self.invoke(text)

    def predict_messages(self, messages: list) -> str:
        if isinstance(messages, list):
            joined = "\n".join(f"{m.get('role','user')}: {m.get('content','')}" for m in messages)
            return self.invoke(joined)
        return self.invoke(str(messages))

    def generate_prompt(self, prompt_value: ChatPromptValue):
        result = self.invoke(prompt_value)
        return Generation(text=result)

    async def apredict(self, text: str) -> str:
        return self.predict(text)

    async def apredict_messages(self, messages: list) -> str:
        return self.predict_messages(messages)

    async def agenerate_prompt(self, prompt_value: ChatPromptValue):
        return self.generate_prompt(prompt_value)