"""S3 tenacity retry tests."""
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError


def _make_client_error(code="ServiceUnavailable"):
    return ClientError(
        error_response={"Error": {"Code": code, "Message": "Transient error"}},
        operation_name="PutObject",
    )


def test_upload_retries_on_transient_error():
    """2 failures + 1 success → upload_bytes succeeds, called 3 times."""
    from app.services.s3 import S3Service

    service = S3Service()
    mock_client = MagicMock()
    call_count = [0]

    def put_side_effect(**kwargs):
        call_count[0] += 1
        if call_count[0] < 3:
            raise _make_client_error()

    mock_client.put_object.side_effect = put_side_effect

    with patch.object(service, "_get_client", return_value=mock_client):
        result = service.upload_bytes("test/key.jpg", b"data", "image/jpeg")

    assert result == "test/key.jpg"
    assert call_count[0] == 3


def test_upload_fails_after_max_retries():
    """3 consecutive failures → raises ClientError."""
    from app.services.s3 import S3Service

    service = S3Service()
    mock_client = MagicMock()
    mock_client.put_object.side_effect = _make_client_error()

    with patch.object(service, "_get_client", return_value=mock_client):
        with pytest.raises(ClientError):
            service.upload_bytes("test/key.jpg", b"data", "image/jpeg")

    assert mock_client.put_object.call_count == 3


def test_delete_retries_on_transient_error():
    """delete_object retries: 2 failures + 1 success → success."""
    from app.services.s3 import S3Service

    service = S3Service()
    mock_client = MagicMock()
    call_count = [0]

    def delete_side_effect(**kwargs):
        call_count[0] += 1
        if call_count[0] < 3:
            raise _make_client_error("RequestTimeout")

    mock_client.delete_object.side_effect = delete_side_effect

    with patch.object(service, "_get_client", return_value=mock_client):
        service.delete_object("test/key.jpg")

    assert call_count[0] == 3


def test_get_bytes_retries_on_transient_error():
    """get_bytes retries: 1 failure + 1 success → returns bytes."""
    from app.services.s3 import S3Service

    service = S3Service()
    mock_client = MagicMock()
    call_count = [0]

    def get_side_effect(**kwargs):
        call_count[0] += 1
        if call_count[0] < 2:
            raise _make_client_error()
        return {"Body": MagicMock(read=lambda: b"content")}

    mock_client.get_object.side_effect = get_side_effect

    with patch.object(service, "_get_client", return_value=mock_client):
        data = service.get_bytes("test/key.jpg")

    assert data == b"content"
    assert call_count[0] == 2


async def test_head_check_404_returns_false():
    """head_check returns False when URL responds with 404."""
    import httpx
    import respx
    from app.services.s3 import S3Service

    service = S3Service()

    with respx.mock:
        respx.head("https://s3.example.com/test/key.jpg").mock(
            return_value=httpx.Response(404)
        )
        async with httpx.AsyncClient() as c:
            result = await service.head_check("https://s3.example.com/test/key.jpg", client=c)

    assert result is False
