import os
import threading
from typing import Optional
import torch
from django.conf import settings  
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM
except Exception:  
    AutoTokenizer = None
    AutoModelForCausalLM = None
    AutoModelForSeq2SeqLM = None


class _LocalModel:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, model_dir: str):
        if AutoTokenizer is None:
            raise RuntimeError("transformers is not installed. Please install the required dependencies.")

        self.model_dir = model_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Try to detect model type: causal or seq2seq
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        model = None
        error_msgs = []

        # 1) Try causal LM
        try:
            model = AutoModelForCausalLM.from_pretrained(self.model_dir)
            self.model_type = "causal"
        except Exception as e:
            error_msgs.append(f"CausalLM load failed: {e}")

        # 2) Fallback to seq2seq
        if model is None:
            try:
                model = AutoModelForSeq2SeqLM.from_pretrained(self.model_dir)
                self.model_type = "seq2seq"
            except Exception as e:
                error_msgs.append(f"Seq2SeqLM load failed: {e}")

        if model is None:
            raise RuntimeError("Could not load local model.\n" + "\n".join(error_msgs))

        self.model = model.to(self.device)
        self.model.eval()

    @classmethod
    def get(cls, model_dir: str):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = _LocalModel(model_dir)
        return cls._instance



    def generate(self, prompt: str, max_new_tokens: int = 128, temperature: float = 0.7) -> str:
        if not prompt:
            return ""

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        gen_kwargs = {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "do_sample": temperature > 0,
            "eos_token_id": self.tokenizer.eos_token_id,
            "pad_token_id": self.tokenizer.eos_token_id,
        }

        with torch.no_grad():
            output_ids = self.model.generate(**inputs, **gen_kwargs)

        if self.model_type == "seq2seq":
            # For seq2seq, generated ids are the decoded output
            text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
            return text.strip()
        else:
            # For causal, decode only the newly generated tokens
            generated_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
            text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
            return text.strip()


def generate_local_response(prompt: str, *, model_dir: Optional[str] = None, max_new_tokens: int = 128, temperature: float = 0.7) -> str:

    
    model_dir = model_dir or getattr(settings, "LOCAL_MODEL_DIR", os.path.join(settings.BASE_DIR, "my_model"))
    instance = _LocalModel.get(str(model_dir))
    return instance.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
