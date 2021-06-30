FROM python:3.9-slim

RUN apt update && apt install -y ffmpeg
ADD requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
ADD main.py /main.py

ENTRYPOINT ["python", "/main.py"]
