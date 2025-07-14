# Use an official Python runtime as the base image

FROM python:3.13.3-alpine

WORKDIR /tcpmesh

RUN apk update && apk add --no-cache \
    git

# Copy the requirements file
#COPY requirements.txt .
#RUN cd /
RUN git clone https://github.com/mayberryjp/tcpmesh /tcpmesh

# Create a virtual environment and install the dependencies
RUN python -m venv venv
RUN venv/bin/pip install --upgrade pip
RUN venv/bin/pip install paho.mqtt
RUN venv/bin/pip install requests

# Run the app
CMD ["venv/bin/python","-u", "tcp_mesh_daemon.py"]