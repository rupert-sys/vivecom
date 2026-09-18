"""
Revisión de code-review: TwilioProvider.send() debía devolver bool según su
propia interfaz (NotificationProvider), pero un error de red en httpx se
propagaba como excepción sin capturar en vez de contarse como "no se pudo
enviar".
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.notification_providers.twilio_provider import TwilioProvider


@pytest.fixture()
def provider():
    return TwilioProvider(account_sid="AC_test", auth_token="token", whatsapp_from="+10000000000", sms_from="+20000000000")


@pytest.mark.asyncio
async def test_send_returns_false_on_network_error_instead_of_raising(provider):
    with patch("httpx.AsyncClient.post", AsyncMock(side_effect=httpx.ConnectError("no se pudo conectar"))):
        resultado = await provider.send("5511112222", "hola")

    assert resultado is False


@pytest.mark.asyncio
async def test_send_returns_false_on_timeout_instead_of_raising(provider):
    """
    F1-35 (QA de entrega, "distintas condiciones de red"): un timeout
    (Twilio lento, no caído del todo) es una excepción DISTINTA a
    ConnectError en httpx (TimeoutException, no ConnectError) — ambas son
    subclases de HTTPError así que el except ya las cubre, pero se agrega
    esta prueba porque un timeout es el escenario de red más realista para
    "Twilio responde lento" y no estaba cubierto explícitamente.
    """
    with patch("httpx.AsyncClient.post", AsyncMock(side_effect=httpx.ReadTimeout("tardó demasiado"))):
        resultado = await provider.send("5511112222", "hola")

    assert resultado is False


@pytest.mark.asyncio
async def test_send_falls_back_to_sms_when_whatsapp_fails(provider):
    respuesta_ok = httpx.Response(status_code=201, request=httpx.Request("POST", "https://x"))
    respuesta_error = httpx.Response(status_code=400, request=httpx.Request("POST", "https://x"))

    with patch("httpx.AsyncClient.post", AsyncMock(side_effect=[respuesta_error, respuesta_ok])) as mock_post:
        resultado = await provider.send("5511112222", "hola")

    assert resultado is True
    assert mock_post.await_count == 2


@pytest.mark.asyncio
async def test_send_returns_true_when_whatsapp_succeeds(provider):
    respuesta_ok = httpx.Response(status_code=201, request=httpx.Request("POST", "https://x"))

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=respuesta_ok)) as mock_post:
        resultado = await provider.send("5511112222", "hola")

    assert resultado is True
    assert mock_post.await_count == 1
