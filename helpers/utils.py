from ninja.responses import Response


def success_response(message="successful", data=None, status=200):
    return Response(data={"message": message, "data": data|dict()}, status=status)

def failure_response(message="failed", status=400):
    return Response(data={"message": message, "data": dict()}, status=status)