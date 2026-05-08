from rest_framework import authentication, exceptions


class WxTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Token"

    def authenticate(self, request):
        token_value = self._get_token_from_request(request)
        if not token_value:
            return None

        from apps.users.models import LoginToken

        token_obj = (
            LoginToken.objects.select_related("user")
            .filter(token=token_value, is_active=True)
            .first()
        )
        if token_obj is None or token_obj.is_expired:
            raise exceptions.AuthenticationFailed("登录态已失效，请重新登录")

        token_obj.touch()
        return (token_obj.user, token_obj)

    def _get_token_from_request(self, request):
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith(f"{self.keyword} "):
            return authorization.split(" ", 1)[1].strip()

        token_value = request.headers.get("X-Token")
        if token_value:
            return token_value.strip()

        return request.query_params.get("token", "").strip() or None

