import os
import threading


class LockManager:
    """
    Gestisce la concorrenza. Impedisce che due utenti scrivano
    sullo stesso file contemporaneamente.
    """

    def __init__(self):
        self.locks = {}  # Dizionario: filename -> owner_id
        self.mutex = threading.Lock()  # Protegge l'accesso al dizionario

    def acquire(self, filename, user_id):
        with self.mutex:
            if filename in self.locks:
                current_owner = self.locks.get(filename)
                if current_owner == user_id:
                    return True  # L'utente ha già il lock
                return False  # File occupato da qualcun altro

            self.locks[filename] = user_id
            print(f"[LOCK] File '{filename}' bloccato da utente {user_id}")
            return True

    def release(self, filename, user_id):
        with self.mutex:
            if filename in self.locks and self.locks.get(filename) == user_id:
                del self.locks[filename]
                print(f"[LOCK] File '{filename}' rilasciato da utente {user_id}")
                return True
            return False


class FileManager:
    """
    La classe che viene esposta in rete.
    Implementa la logica di gestione file.
    """

    def __init__(self, lock_manager, storage_dir):
        self.lock_manager = lock_manager
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def list_files(self):
        return os.listdir(self.storage_dir)

    def get_file_size(self, filename):
        path = os.path.join(self.storage_dir, filename)
        if os.path.exists(path):
            return os.path.getsize(path)
        return -1

    def create_empty(self, filename, user_id):
        """Prepara un file vuoto per la scrittura (sovrascrittura)."""
        if not self._check_lock(filename, user_id):
            raise PermissionError("File bloccato da un altro utente.")

        path = os.path.join(self.storage_dir, filename)
        with open(path, "wb") as f:
            pass  # Crea file vuoto
        return True

    def write_chunk(self, filename, data, user_id):
        """Scrive una porzione di dati in append."""
        if not self._check_lock(filename, user_id):
            raise PermissionError("File bloccato da un altro utente.")

        path = os.path.join(self.storage_dir, filename)
        with open(path, "ab") as f:  # Append Binary
            f.write(data)
        return True

    def read_chunk(self, filename, offset, size):
        """Legge una porzione di dati."""
        path = os.path.join(self.storage_dir, filename)
        if not os.path.exists(path):
            return None

        with open(path, "rb") as f:
            f.seek(offset)
            data = f.read(size)
        return data

    def delete_file(self, filename, user_id):
        if not self._check_lock(filename, user_id):
            raise PermissionError("File bloccato da un altro utente.")

        path = os.path.join(self.storage_dir, filename)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def _check_lock(self, filename, user_id):
        """Helper interno per verificare se l'utente possiede il lock."""
        with self.lock_manager.mutex:
            if filename in self.lock_manager.locks:
                return self.lock_manager.locks.get(filename) == user_id
            return True
