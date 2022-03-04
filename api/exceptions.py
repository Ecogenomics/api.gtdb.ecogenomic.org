from fastapi import HTTPException


class HttpBadRequest(HTTPException):
    status_code = 400

    def __init__(self, detail):
        super().__init__(status_code=self.status_code, detail=detail)


class HttpNotFound(HTTPException):
    status_code = 404

    def __init__(self, detail):
        super().__init__(status_code=self.status_code, detail=detail)


class HttpInternalServerError(HTTPException):
    status_code = 500

    def __init__(self, detail):
        super().__init__(status_code=self.status_code, detail=detail)
