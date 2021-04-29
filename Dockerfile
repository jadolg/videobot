FROM python:3.8-slim

RUN apt update && apt install -y ffmpeg
ADD requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
ADD main.py /main.py

ENTRYPOINT ["python", "/main.py"]
