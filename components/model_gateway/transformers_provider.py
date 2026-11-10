import asyncio
import time
from uuid import uuid4

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from contracts.model.model_request import ModelRequest
from contracts.model.model_response import ModelResponse
from components.model_gateway.model_config import LocalModelConfig
from components.model_gateway.provider import ModelProvider


class LocalTransformersProvider(ModelProvider):
    """
    Loads models 100% offline from local disk caches (Hugging Face or ModelScope).
    Handles both Base and Instruct models cleanly.
    """

    def __init__(self, config: LocalModelConfig):
        self.config = config
        self.tokenizer = None
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        source = (self.config.source or "modelscope").lower()
        source_label = "Hugging Face Cache" if source == "huggingface" else "ModelScope Cache"

        print(f"[INFO] Loading model '{self.config.model_id}' from local {source_label}...", end="", flush=True)

        if source == "huggingface":
            model_path = self.config.model_id
        else:
            from modelscope import snapshot_download
            model_path = snapshot_download(
                self.config.model_id,
                local_files_only=True,
            )

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            local_files_only=True,
            trust_remote_code=self.config.trust_remote_code,
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            local_files_only=True,
            torch_dtype=self.config.torch_dtype,
            device_map=self.config.device_map,
            trust_remote_code=self.config.trust_remote_code,
        )

        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        self.model.eval()
        print(" Ready!")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Model provider is not initialized.")

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        # 1. Try Chat Template if available (Instruct models)
        if getattr(self.tokenizer, "chat_template", None) is not None:
            try:
                text = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=False,
                )
            except (TypeError, ValueError):
                text = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
        else:
            # 2. Clean fallback for Base models
            system_part = f"{request.system_prompt}\n\n" if request.system_prompt else ""
            text = f"{system_part}User: {request.prompt}\n\nAssistant:"

        model_inputs = self.tokenizer([text], return_tensors="pt")
        model_inputs = model_inputs.to(self.model.device)
        input_token_count = model_inputs.input_ids.shape[-1]

        start_time = time.perf_counter()

        # Run blocking PyTorch generation in a worker thread to keep event loop free
        def _run_inference():
            with torch.inference_mode():
                return self.model.generate(
                    **model_inputs,
                    max_new_tokens=(request.max_tokens or self.config.max_new_tokens),
                    temperature=request.temperature,
                    top_p=request.top_p,
                    top_k=request.top_k,
                    pad_token_id=self.tokenizer.pad_token_id,
                    do_sample=(request.temperature > 0),
                )

        generated_ids = await asyncio.to_thread(_run_inference)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        generated_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        output_token_count = len(generated_ids[0])

        content = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

        return ModelResponse(
            response_id=str(uuid4()),
            content=content,
            model_name=request.model,
            tokens_input=input_token_count,
            tokens_output=output_token_count,
            latency_ms=latency_ms,
            metadata={
                "provider": "local_transformers",
                "source": self.config.source,
            },
        )

    async def health_check(self) -> bool:
        return self.model is not None and self.tokenizer is not None
