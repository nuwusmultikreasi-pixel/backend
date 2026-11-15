# Gunakan PyMySQL sebagai driver MySQL (tidak perlu compile mysqlclient di Windows)
try:
    import pymysql

    pymysql.version_info = (2, 2, 4, "final", 0)
    pymysql.install_as_MySQLdb()
except ImportError:  # pragma: no cover
    pass
