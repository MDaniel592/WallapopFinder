# Wallapop Finder

Contenedor docker utilizado para buscar productos en wallapop.

## Software Requirements
- Docker
- Docker-compose

## Telegram Requirements
- El token del bot de Telegram
- Tú identificador (ID) de usuario en Telegram

## Antes de hacer el deploy con docker (primera vez):
- Crea un nuevo archivo con el nombre 'private_data.py' y pega las siguientes variables:
    ```
    DEVELOPER_CHAT_ID = XXXX
    BOT_TOKEN = YYYY
    ```
    - Las XXXX corresponden a tu ID de telegram
    - Las YYYY corresponden al token del bot de Telegram

## Consideraciones
- La base de datos (sqlite_wallapop) está creado, pero sin entradas

## Ejecución

Una vez hayas completado el paso anterior, ya puedes crear el contenedor: 
```
docker-compose build && docker-compose up -d
```
## Disclamer
Actualmente, solo puedes buscar en una única categoría. En este caso se ha selecionado la categoría 'MOTOS'.
Esta categoría puede cambiarse en el módulo 'wallapop.py'

Por defecto, el uso del bot está limitado al identificador de usuario en Telegram que introduzcas en el fichero 'private_data.py'.

**NO tengo intención de mejorar o desarrollar este repositorio. Si quieres mejorar el código, abre un pull request.**