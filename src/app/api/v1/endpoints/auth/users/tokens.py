import fastapi

router = fastapi.APIRouter()


@router.post("")
def create_jwt_token():
    return {"access_token": "access_token", "refresh_token": "refresh_token"}


@router.get("/info")
def get_jwt_token_info():
    return {"username": "test"}
