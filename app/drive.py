import psutil

# Получить все сетевые соединения
for conn in psutil.net_connections(kind='inet'):
    print(conn)
