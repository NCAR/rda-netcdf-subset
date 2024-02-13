from fastapi import APIRouter
import dsrqst_netcdf_commandlist

router = APIRouter()

@router.get("/")
def netcdf_subset():
    return dsrqst_netcdf_commandlist