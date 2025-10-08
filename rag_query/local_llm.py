from typing import Any, List
from transformers import AutoTokenizer, AutoModelForCausalLM
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.language_models import BaseLanguageModel
from langchain_core.outputs import Generation
from pydantic import PrivateAttr, ConfigDict  # v2
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
            torch_dtype=torch.float16,
        )

    def invoke(self, prompt: str, config=None, **kwargs) -> str:
        if isinstance(prompt, ChatPromptValue):
            prompt = prompt.to_string()

        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        outputs = self._model.generate(
            **inputs,
            max_new_tokens=self.max_tokens,
            temperature=0.3,
            top_p=0.9,
            do_sample=True,
            eos_token_id=self._tokenizer.eos_token_id,
        )
        return self._tokenizer.decode(outputs[0], skip_special_tokens=True)

    def stream(self, prompt: str):
        yield self.invoke(prompt)

    def batch(self, prompts: List[str]) -> List[str]:
        return [self.invoke(p) for p in prompts]

    def bind(self, **kwargs):
        return self

    def predict(self, text: str) -> str:
        return self.invoke(text)

    def predict_messages(self, messages: list) -> str:
        prompt = "\n".join([msg.content for msg in messages])
        return self.invoke(prompt)

    def generate_prompt(self, prompt_value):
        result = self.invoke(prompt_value.to_string())
        return Generation(text=result)

    async def apredict(self, text: str) -> str:
        return self.predict(text)

    async def apredict_messages(self, messages: list) -> str:
        return self.predict_messages(messages)

    async def agenerate_prompt(self, prompt_value):
        return self.generate_prompt(prompt_value)