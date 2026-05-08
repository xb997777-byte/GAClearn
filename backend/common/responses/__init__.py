from rest_framework.response import Response


def success_response(data=None, message="ok", status_code=200):
    return Response(
        {
            "code": 0,
            "message": message,
            "data": data if data is not None else {},
        },
        status=status_code,
    )


def error_response(message="error", code=40000, status_code=400, data=None):
    return Response(
        {
            "code": code,
            "message": message,
            "data": data,
        },
        status=status_code,
    )

