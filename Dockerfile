FROM python:3.11-bullseye
WORKDIR /data/work
COPY requirements.txt . 

# Set up environment
RUN apt-get update && apt-get install -y gcc libc-dev gfortran g++ libhdf5-serial-dev libnetcdf-dev
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY netcdf_subset/* /data/work/

ENV PATH="${PATH}:/data/work/"

RUN chmod 755 /data/work/dsrqst_netcdf_commandlist.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
