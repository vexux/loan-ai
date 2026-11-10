import asyncio
import os
import time
from uuid import uuid4
from llama_cpp import Llama

from contracts.model.model_request import ModelRequest
from contracts.model.model_response import ModelResponse
from components.model_gateway.provider import ModelProvider


class LlamaCppGGUFProvider(ModelProvider):
    """
    100% offline GGUF model provider using llama-cpp-python.
    Natively supports Llama 3.2 Instruct chat templates and token counting.
    """

    def __init__(self, model_path: str, n_ctx: int = 2048, n_threads: int = 6, n_gpu_layers: int = 0):
        self.model_path = os.path.abspath(model_path)
        model_name = os.path.splitext(os.path.basename(self.model_path))[0]
        print(f"[INFO] Loading model '{model_name}'...", end="", flush=True)

        
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,  # Set > 0 if you have CUDA/Metal
            verbose=False,
        )
        print(" Ready!")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        start_time = time.perf_counter()

        def _run_inference():
            return self.llm.create_chat_completion(
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                top_k=request.top_k,
                repeat_penalty=1.2,
            )

        # Run blocking C++ inference in a worker thread to keep asyncio event loop responsive
        output = await asyncio.to_thread(_run_inference)
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        content = output["choices"][0]["message"]["content"] or ""
        tokens_input = output.get("usage", {}).get("prompt_tokens", 0)
        tokens_output = output.get("usage", {}).get("completion_tokens", 0)

        return ModelResponse(
            response_id=str(uuid4()),
            content=content.strip(),
            model_name=os.path.basename(self.model_path),
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            metadata={
                "provider": "llama_cpp_gguf",
                "model_path": self.model_path,
            },
        )

    async def health_check(self) -> bool:
        return self.llm is not None
