import os
from multiprocessing.managers import BaseManager
from pydfs.managers import FileManager, LockManager
from pydfs.config import SERVER_PORT, AUTH_KEY, STORAGE_DIR

# --- Setup del Server RMI ---
def start_server():
    # Istanziamo i gestori
    lock_mgr = LockManager()
    file_mgr = FileManager(lock_mgr, STORAGE_DIR)

    # Registriamo le classi
    BaseManager.register("get_file_manager", callable=lambda: file_mgr)
    BaseManager.register("get_lock_manager", callable=lambda: lock_mgr)

    manager = BaseManager(address=("", SERVER_PORT), authkey=AUTH_KEY)
    server = manager.get_server()

    print(f"[SERVER] PyDFS Server avviato sulla porta {SERVER_PORT}...")
    print(f"[SERVER] Cartella storage: {os.path.abspath(STORAGE_DIR)}")
    server.serve_forever()


if __name__ == "__main__":
    start_server()
