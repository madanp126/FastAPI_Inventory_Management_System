from fastapi import FastAPI, APIRouter

router=APIRouter()

@router.get('/test')
def inventory_test():
    return {'message': 'Inventory router is working'}