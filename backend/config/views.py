"""Views de infraestrutura, sem relação com regras de negócio."""
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
def health_check(request: Request) -> Response:
    """Confirma que a API está no ar e respondendo."""
    return Response({"status": "ok"})
