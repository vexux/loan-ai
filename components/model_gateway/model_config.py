from dataclasses import dataclass


@dataclass(frozen=True)
class LocalModelConfig:
    """
    Configuration for loading models strictly from local caches.
    Supported sources:
      - 'modelscope'  -> reads from local ~/.cache/modelscope/
      - 'huggingface' -> reads from local ~/.cache/huggingface/
    """

    model_id: str
    source: str = "modelscope"
    device_map: str = "auto"
    torch_dtype: str = "auto"
    trust_remote_code: bool = False
    max_new_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 20
    do_sample: bool = True
