# eRaspberry
Eibriel service for Raspberry Linux

## Disable BLANK and POWERDOWN
### Method 1
You need to edit the following file /etc/kbd/config

`sudo nano /etc/kbd/config`

then change

`BLANK_TIME=X`

to

`BLANK_TIME=0`

and

`POWERDOWN_TIME=X`

to

`POWERDOWN_TIME=0`

### Method 2
`sudo nano /etc/lightdm/lightdm.conf`

In that file, look for:
`[SeatDefault]`

and insert this line:
`xserver-command=X -s 0 dpms`

then reboot

## Enable USB Mic

**Cada vez que se inicia sesión en el OS**

`nano ~/.asoundrc`

change `card 0` to `card 1` in both lines

*¡Tocar las opciones de sonido reiniciará la configuración y habrá que volver a modificar el archivo!*

## Installation

```
cd ~
mkdir dev
cd dev
mkdir eRaspberry
cd eRaspberry
sudo apt install virtualenv libasound2-dev
virtualenv -p python3 venv
. venv/bin/activate
git clone https://github.com/EibrielOrg/eRaspberry.git
cd eRaspberry
pip install -r requirements.txt
```

## Actualización
```
git remote set-url origin https://github.com/Eibriel/eRaspberry.git
git pull
```
Agregar las líneas a `config.py`
```
RATE_RECORD = 44100 # Mic rateframe
RATE_SEND = 16000 # Rateframe reported to IBM SST
```


## Configuración

Copiar archivo `config.py` en la misma carpeta donde está eRaspberry.py

Estructura del archivo de configuración:

```
class Config:
    WATSON_TTS_USERNAME = ""
    WATSON_TTS_PASSWORD = ""

    WATSON_CON_USERNAME = ""
    WATSON_CON_PASSWORD = ""
    WORKSPACE_ID = ""

    EMAIL_USER = "mg54_puerta@eibriel.com"
    EMAIL_PASS = ""

    EMAILS = {
        "Nombre": ["correo@correo.com"], # El nombre debe coincidir con Watson
    }
    EMAIL_DEFAULT = ["correo@correo.com"] # Correo al cual se notificará si el anfitrion no es conocido
    EMAIL_TEST = True # Set to False to actually send emails
    EMAIL_DRY = False # Set to False to actually send emails

    MIC_TRESHOLD = 10000 # Numeros mas bajos vuelven el mic mas sensible, mas altos menos sensible
    RATE_RECORD = 44100 # Mic rateframe
    RATE_SEND = 16000 # Rateframe reported to IBM SST
```

Valores posibles para los rates:

- 8000
- 11025
- 16000
- 22050
- 32000
- 44100
- 48000


## Uso

Iniciar el servidor con el comando

```
cd ~/dev/eRaspberry/eRaspberry
. ../venv/bin/activate
python eRaspberry.py
```

En una nueva pestaña de la terminal iniciar el servidor web con el comando

```
cd ~/dev/eRaspberry/eRaspberry
. ../venv/bin/activate
python eRaspberry_server.py
```

Acceder a la interfaz web en el navegador usando la dirección: http://0.0.0.0:500/start

En Chromium tocar F11 para pasar a modo de pantalla completa

## Actualización

Cerrar ambos servidores utilizando el comando `Ctrl+C` múltiples veces (hasta que el programa se cierre completamente)

```
cd ~/dev/eRaspberry/eRaspberry
git pull --rebase
```

Si el archivo `config.py` se modificó reemplazarlo por la nueva versión

Luego volver a iniciar los servidores, y acceder nuevamente a http://0.0.0.0:5000/start
