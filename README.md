WazApp Desktop
==============
WazApp Desktop is a desktop (Qt) based GUI for the WhatsApp protocol.
It uses the Yowsup library for the communication: https://github.com/tgalal/yowsup

Install
=======
- clone wazapp-desktop
    - git clone https://github.com/DorianScholz/wazapp-desktop.git
- on the first start it will download the Yowsup library
    - in case that fails, clone my Yowsup fork and put it in your python path before starting wazapp-desktop
        - git clone https://github.com/DorianScholz/yowsup.git

Prerequisites
=============
- Python
- PyQt4
- python-gdata (only for google contacts sync)
