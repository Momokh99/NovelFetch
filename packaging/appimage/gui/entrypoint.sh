#!/bin/sh
# python-appimage template: {{ python-executable }} resolves to the
# bundled Python interpreter inside $APPDIR.
exec {{ python-executable }} -m gui.main "$@"
