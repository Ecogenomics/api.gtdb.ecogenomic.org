import base64


def base64url_to_str(encoded):
    encoded = encoded.replace('~', '=').replace('.', '+').replace('_', '/')
    return base64.decodebytes(encoded.encode()).decode()
