import google.generativeai as genai
from django.conf import settings
from google.ai import generativelanguage as glm
from google.auth import exceptions as ga_exceptions
from providers.serializers import (
    PromptSerializer,
    ProviderResponseSerializer,
    build_prompt_gemini,
)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


def get_client(key=None):
    if key is None:
        key = settings.GEMINI_API_KEY
    return glm.GenerativeServiceClient(client_options={"api_key": key})


class GeminiViewSet(ViewSet):

    @action(detail=False, url_path="status", url_name="status")
    def status(self, request):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        try:
            list(genai.list_models())
        except ga_exceptions.DefaultCredentialsError:
            context = (
                "GEMINI_API_KEY não encontrada. Por favor, veja como criar uma em "
                '"https://ai.google.dev/gemini-api/docs/oauth" e adicione ao arquivo de configuração.'
            )
            return Response({"status": "unavailable provider", "context": context}, status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"status": "running"}, status.HTTP_200_OK)

    @action(detail=False, url_path="models", url_name="models")
    def models(self, request):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        content = {
            "models": [m.name[7:] for m in genai.list_models() if "generateContent" in m.supported_generation_methods],
        }
        return Response(content, status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["POST"],
        url_path="prompt",
        url_name="prompt",
    )
    def prompt(self, request):
        data = JSONParser().parse(request)
        prompt = PromptSerializer(data=data)

        if prompt.is_valid():
            client = get_client(key=prompt.validated_data.get("key", None))
            model = genai.GenerativeModel(prompt.validated_data["model"])
            model._client = client
            response = model.generate_content(
                build_prompt_gemini(prompt.validated_data["prompt"]),
            )
            provider_response = ProviderResponseSerializer(data={"provider": "gemini", "response": response.text})
            assert provider_response.is_valid()
            return Response(provider_response.data, status.HTTP_200_OK)
        return Response(prompt.errors, status.HTTP_400_BAD_REQUEST)
