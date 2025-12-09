import sys
import os
import uuid
from multiprocessing.managers import BaseManager
from pydfs.config import SERVER_ADDRESS, SERVER_PORT, AUTH_KEY, CHUNK_SIZE


class DFSClient:
    def __init__(self):
        # Generiamo un ID univoco per questo client (per i lock)
        self.user_id = str(uuid.uuid4())[:8]
        print(f"[INIT] Client ID assegnato: {self.user_id}")

        # Creiamo la cartella di storage del client
        self.storage_dir = "client_storage"
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
        print(f"[INIT] Cartella di storage locale: '{self.storage_dir}'")

        self.connect()

    def connect(self):
        BaseManager.register("get_file_manager")
        BaseManager.register("get_lock_manager")

        self.manager = BaseManager(
            address=(SERVER_ADDRESS, SERVER_PORT), authkey=AUTH_KEY
        )
        try:
            self.manager.connect()
            self.fm = self.manager.get_file_manager()
            self.lm = self.manager.get_lock_manager()
            print("[INIT] Connesso al server PyDFS.")
        except ConnectionRefusedError:
            print("[ERROR] Impossibile connettersi al server. E' attivo?")
            sys.exit(1)

    def do_list(self):
        try:
            files = self.fm.list_files()
            print("\n--- File sul Server ---")
            if not files:
                print("(Nessun file presente)")
            for f in files:
                size = self.fm.get_file_size(f)
                print(f"- {f} \t({size} bytes)")
            print("-----------------------")
        except Exception as e:
            print(f"Errore listing: {e}")

    def do_upload(self, local_path):
        # Se il percorso è relativo, lo consideriamo interno alla nostra cartella
        if not os.path.isabs(local_path):
            local_path = os.path.join(self.storage_dir, local_path)

        if not os.path.exists(local_path):
            print(f"File locale '{local_path}' non trovato.")
            return

        filename = os.path.basename(local_path)
        file_size = os.path.getsize(local_path)

        print(f"Richiesta di upload per '{filename}'...")

        # 1. Acquisizione Lock
        if not self.lm.acquire(filename, self.user_id):
            print(
                f"[ERROR] Il file '{filename}' è bloccato da un altro utente! Riprova più tardi."
            )
            return

        try:
            # 2. Creazione file vuoto
            self.fm.create_empty(filename, self.user_id)

            # 3. Trasferimento a blocchi
            sent_bytes = 0
            with open(local_path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    self.fm.write_chunk(filename, chunk, self.user_id)

                    sent_bytes += len(chunk)
                    # Barra progresso semplice
                    progress = int((sent_bytes / file_size) * 100)
                    print(f"\rUpload: {progress}% completato", end="")

            print(f"\n[SUCCESS] File '{filename}' caricato correttamente.")

        except Exception as e:
            print(f"\n[ERROR] Upload fallito: {e}")
        finally:
            # 4. Rilascio Lock (Sempre, anche se c'è errore)
            self.lm.release(filename, self.user_id)

    def do_download(self, filename):
        file_size = self.fm.get_file_size(filename)
        if file_size == -1:
            print("File remoto non trovato.")
            return

        print(f"Inizio download di '{filename}' ({file_size} bytes)...")

        local_save_path = os.path.join(self.storage_dir, filename)

        # Opzionale: Lock in lettura? Per ora no, permettiamo lettura concorrente.

        try:
            with open(local_save_path, "wb") as f:
                offset = 0
                while offset < file_size:
                    chunk = self.fm.read_chunk(filename, offset, CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    offset += len(chunk)

                    progress = int((offset / file_size) * 100)
                    print(f"\rDownload: {progress}% completato", end="")

            print(f"\n[SUCCESS] File salvato come '{local_save_path}'.")

        except Exception as e:
            print(f"\n[ERROR] Download fallito: {e}")

    def do_delete(self, filename):
        print(f"Tentativo eliminazione '{filename}'...")

        if not self.lm.acquire(filename, self.user_id):
            print("[ERROR] File in uso da altro utente.")
            return

        try:
            res = self.fm.delete_file(filename, self.user_id)
            if res:
                print("[SUCCESS] File eliminato.")
            else:
                print("[ERROR] Impossibile eliminare (forse non esiste).")
        except Exception as e:
            print(f"Errore delete: {e}")
        finally:
            self.lm.release(filename, self.user_id)

    def interactive_shell(self):
        print("\n=== PyDFS Client Shell ===")
        print("Comandi disponibili: ls, up <file>, down <file>, rm <file>, exit")

        while True:
            try:
                cmd_line = input("\nPyDFS> ").strip().split()
                if not cmd_line:
                    continue

                cmd = cmd_line[0].lower()

                if cmd == "exit":
                    break
                elif cmd == "ls":
                    self.do_list()
                elif cmd == "up":
                    if len(cmd_line) < 2:
                        print("Uso: up <local_filename>")
                        continue
                    self.do_upload(cmd_line[1])
                elif cmd == "down":
                    if len(cmd_line) < 2:
                        print("Uso: down <remote_filename>")
                        continue
                    self.do_download(cmd_line[1])
                elif cmd == "rm":
                    if len(cmd_line) < 2:
                        print("Uso: rm <remote_filename>")
                        continue
                    self.do_delete(cmd_line[1])
                else:
                    print("Comando sconosciuto.")

            except KeyboardInterrupt:
                break
        print("\nBye!")


def main():
    client = DFSClient()
    client.interactive_shell()


if __name__ == "__main__":
    main()

