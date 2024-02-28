FROM python:3.11-bullseye
WORKDIR /data/work
COPY requirements.txt . 
RUN echo 'APT::Sandbox::User "root";' > /etc/apt/apt.conf.d/sandbox-disable
# Set up environment
RUN apt-get update 
RUN apt-get install -y gcc libc-dev gfortran g++ libhdf5-serial-dev libnetcdf-dev
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY netcdf_subset/* .

ENV PATH="${PATH}:/data/work/"

RUN chmod 755 /data/work/dsrqst_netcdf_commandlist.py

ENTRYPOINT ["dsrqst_netcdf_commandlist.py"]
CMD ["-h"]
