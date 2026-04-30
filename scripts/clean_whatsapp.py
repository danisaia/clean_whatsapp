#!/usr/bin/env python3
from __future__ import annotations

import sys

from clean_whatsapp_app.app import main
from clean_whatsapp_app.i18n import I18n


if sys.version_info < (3, 10):
    print("Clean WhatsApp needs Python 3.10 or newer.")
    print("Português: o Clean WhatsApp precisa do Python 3.10 ou mais novo.")
    print("Español: Clean WhatsApp necesita Python 3.10 o más reciente.")
    print("Français : Clean WhatsApp nécessite Python 3.10 ou plus récent.")
    sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + I18n().t("interrupted"))
