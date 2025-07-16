from fastapi import FastAPI, APIRouter

router=APIRouter()

@router.get('/test')
def user_test():
    return {'message': 'User router is working'}