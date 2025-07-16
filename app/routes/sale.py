from fastapi import FastAPI, APIRouter

router=APIRouter()

@router.get('/test')
def sale_test():
    return {'message': 'Sale router is working'}