class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # enable cors for api requests
        if request.path.startswith("/api/v"):
            response["Access-Control-Allow-Origin"] = "*"
        return response
