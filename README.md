# beeves-speech-server
The hotword detection and ASR server for Beeves

Extract this file so that you have a directory named `Porcupine/` in the root directory:

`https://github.com/Picovoice/Porcupine/archive/v1.6.tar.gz`

then:

```
python3 -m venv venv
pip3 install -r Porcupine/requirements.txt
pip3 install -r ./requirements.txt
```


Then:

```
./beeves-speech-server.py
```

