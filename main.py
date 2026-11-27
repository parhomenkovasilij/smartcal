"""Точка входу SmartCal."""
from smartcal.gui import MainWindow
from smartcal.service import SmartCalService
from smartcal.storage import Storage


def main():
    app = MainWindow(SmartCalService(Storage("smartcal.db")))
    app.mainloop()


if __name__ == "__main__":
    main()
