"""Bound incoming API bodies before JSON parsing or domain side effects."""
import asyncio
from uuid import uuid4
from starlette.responses import JSONResponse


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class RequestLimits:
    def __init__(self, app, max_bytes, body_seconds):
        self.app, self.max_bytes, self.body_seconds = app, max_bytes, body_seconds

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/v1/"):
            return await self.app(scope, receive, send)
        correlation = scope.setdefault("state", {}).setdefault("correlation_id", str(uuid4()))

        async def reject(status, code, message):
            response = JSONResponse({"code": code, "message": message, "correlation_id": correlation}, status_code=status,
                headers={**SECURITY_HEADERS, "X-Correlation-ID": correlation, "Cache-Control": "no-store"})
            await response(scope, receive, send)

        lengths = [v for k, v in scope["headers"] if k.lower() == b"content-length"]
        declared = None
        if lengths:
            try:
                if len(lengths) != 1 or not lengths[0].isdigit():
                    raise ValueError
                declared = int(lengths[0])
            except ValueError:
                return await reject(400, "REQUEST_FRAMING", "Tamanho de requisição inválido.")
            if declared > self.max_bytes:
                return await reject(413, "REQUEST_TOO_LARGE", "A requisição excede o limite permitido.")
        if any(k.lower() == b"content-encoding" and v.lower().strip() != b"identity" for k, v in scope["headers"]):
            return await reject(415, "REQUEST_ENCODING", "Envie o conteúdo sem compressão.")
        chunks, size = [], 0
        try:
            async with asyncio.timeout(self.body_seconds):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    size += len(chunk)
                    if size > self.max_bytes:
                        return await reject(413, "REQUEST_TOO_LARGE", "A requisição excede o limite permitido.")
                    chunks.append(chunk)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            return await reject(408, "REQUEST_BODY_TIMEOUT", "Tempo de recebimento da requisição excedido.")
        if declared is not None and size != declared:
            return await reject(400, "REQUEST_FRAMING", "Tamanho de requisição divergente.")
        body, sent = b"".join(chunks), False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
