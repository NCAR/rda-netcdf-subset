from fastapi import APIRouter
#import dsrqst_netcdf_commandlist

router = APIRouter()

@router.get("/hello")
def hello():
    return {"message": "hello"}

'''
@router.get("/netcdf_subset")
def netcdf_subset():
    data = dsrqst_netcdf_commandlist()
    return data
'''