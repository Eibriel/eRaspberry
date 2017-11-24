# eRaspberry
Eibriel service for Raspberry Linux

## Disable BLANK and POWERDOWN

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

then reboot

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

## Configuración

Copiar archivo config.py en la misma carpeta donde está eRaspberry.py


## Uso

Iniciar el servidor con el comando

```
cd ~/dev/eRaspberry/eRaspberry
. ../venv/bin/activate
python eRaspberry_server.py
```

En una nueva pestaña de la terminal iniciar el servidor web con el comando

```
cd ~/dev/eRaspberry/eRaspberry
. ../venv/bin/activate
python eRaspberry_server.py
```

Acceder a la interfaz web en el navegador usando la dirección: http://0.0.0.0:500/ui

## Actualización

Cerrar ambos servidores utilizando el comando `Ctrl+C` múltiples veces (hasta que el programa se cierre completamente)

```
cd ~/dev/eRaspberry/eRaspberry
git pull --rebase
```
Luego volver a iniciar los servidores
