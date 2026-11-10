from components.model_gateway.gateway import ModelGateway
from components.model_gateway.model_config import LocalModelConfig
from components.model_gateway.transformers_provider import LocalTransformersProvider
from components.model_gateway.gateway import ModelGateway
from components.model_gateway.gguf_provider import LlamaCppGGUFProvider

def create_local_model_gateway(
    model_id: str = "Qwen/Qwen3-0.6B",
    source: str = "modelscope",
) -> ModelGateway:
    config = LocalModelConfig(
        model_id=model_id,
        source=source,
    )
    provider = LocalTransformersProvider(
        config=config,
    )
    return ModelGateway(
        provider=provider,
    )


def create_gguf_model_gateway(
    model_path: str,
    n_ctx: int = 4096,
) -> ModelGateway:
    # Lazy import so other providers don't crash if llama-cpp is missing
    from components.model_gateway.gguf_provider import LlamaCppGGUFProvider
    
    provider = LlamaCppGGUFProvider(model_path=model_path, n_ctx=n_ctx)
    return ModelGateway(provider=provider)

