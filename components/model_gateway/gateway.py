from contracts.model.model_request import ModelRequest
from contracts.model.model_response import ModelResponse
from contracts.model.model_gateway_contract import ModelGatewayContract
from components.model_gateway.provider import ModelProvider


class ModelGateway(ModelGatewayContract):
    """
    Technology-agnostic gateway exposed to the Agent Core.
    """

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    async def generate(self, request: ModelRequest) -> ModelResponse:
        return await self.provider.generate(request)

    async def health_check(self) -> bool:
        return await self.provider.health_check()
