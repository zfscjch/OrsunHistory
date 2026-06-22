class Config:
    MAINTENANCE_MODE = False
    ALLOWED_DIR = "doc"
    STANDARD_PASSWORD = ""
    MASTER_PASSWORD = ""
    writer = []
    MySQLConfig = {
        "user": "YourMySQLUserName",
        "password": "YourMySQLPassword",
        "host": "localhost",
        "port": 3306,
        "database": "blog_db",
        "use_pure": True,
        "raise_on_warnings": True
    }


    @classmethod
    def change_maintenance(cls):
        cls.MAINTENANCE_MODE = not cls.MAINTENANCE_MODE

    @classmethod
    def set_maintenance(cls, val):
        cls.MAINTENANCE_MODE = val