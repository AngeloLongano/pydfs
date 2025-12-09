import unittest
import os
import subprocess
import time
import shutil
import argparse
import sys
import contextlib
from client import DFSClient
from pydfs.config import STORAGE_DIR

class TestPyDFS(unittest.TestCase):
    server_process = None
    cleanup = False

    @classmethod
    def setUpClass(cls):
        # Avvia il server una sola volta per tutti i test
        cls.server_process = subprocess.Popen(
            ["python", "server.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("Avvio del server in corso...")
        time.sleep(2)  # Diamo tempo al server di avviarsi

    @classmethod
    def tearDownClass(cls):
        # Ferma il server alla fine di tutti i test
        cls.server_process.terminate()
        cls.server_process.wait()
        print("\nServer fermato.")
        if cls.cleanup:
            print("Pulizia finale delle cartelle di storage...")
            if os.path.exists(STORAGE_DIR):
                shutil.rmtree(STORAGE_DIR)
            if os.path.exists("client_storage"):
                shutil.rmtree("client_storage")

    def setUp(self):
        # Pulizia prima di ogni test per garantire l'isolamento
        if os.path.exists(STORAGE_DIR):
            shutil.rmtree(STORAGE_DIR)
        os.makedirs(STORAGE_DIR)

        if os.path.exists("client_storage"):
            shutil.rmtree("client_storage")
        
        # Redirige stdout per non mostrare l'output del costruttore del client
        with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
            self.client = DFSClient()

        self.test_filename = "test_file.txt"
        self.test_content = "Questo è un file di test."
        self.local_test_filepath = os.path.join(self.client.storage_dir, self.test_filename)
        self.server_test_filepath = os.path.join(STORAGE_DIR, self.test_filename)

        with open(self.local_test_filepath, "w") as f:
            f.write(self.test_content)

    def tearDown(self):
        # Il cleanup viene fatto da setUp() del test successivo,
        # questo permette di ispezionare lo stato dopo ogni test se non si usa --cleanup
        pass

    def test_upload(self):
        with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
            self.client.do_upload(self.test_filename)
        self.assertTrue(os.path.exists(self.server_test_filepath), "Il file non è stato caricato sul server")

    def test_list(self):
        with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
            self.client.do_upload(self.test_filename)
        
        files = self.client.fm.list_files()
        self.assertIn(self.test_filename, files, "Il file caricato non appare nella lista")

    def test_download(self):
        with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
            self.client.do_upload(self.test_filename)
            os.remove(self.local_test_filepath)
            self.client.do_download(self.test_filename)
        
        self.assertTrue(os.path.exists(self.local_test_filepath), "Il file non è stato scaricato")
        with open(self.local_test_filepath, "r") as f:
            self.assertEqual(f.read(), self.test_content, "Il contenuto del file non corrisponde")

    def test_delete(self):
        with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
            self.client.do_upload(self.test_filename)
            self.assertTrue(os.path.exists(self.server_test_filepath), "Setup fallito: il file non è stato caricato")
            self.client.do_delete(self.test_filename)
        
        self.assertFalse(os.path.exists(self.server_test_filepath), "Il file non è stato eliminato dal server")

def main():
    parser = argparse.ArgumentParser(description="Esegue i test per PyDFS.")
    parser.add_argument('--cleanup', action='store_true', help='Esegue la pulizia delle cartelle di storage dopo i test.')
    args, unknown = parser.parse_known_args()

    TestPyDFS.cleanup = args.cleanup

    # Pulizia iniziale una tantum
    if os.path.exists(STORAGE_DIR):
        shutil.rmtree(STORAGE_DIR)
    if os.path.exists("client_storage"):
        shutil.rmtree("client_storage")

    print("ATTENZIONE: Questi test creano/modificano le cartelle 'server_storage' e 'client_storage'.")
    if args.cleanup:
        print("L'opzione --cleanup è attiva: le cartelle verranno eliminate al termine dei test.")
    else:
        print("Le cartelle NON verranno eliminate, per permettere l'ispezione manuale.")
    
    print("Esecuzione test in 3 secondi...")
    time.sleep(3)

    # Esegui unittest con gli argomenti non riconosciuti
    unittest.main(argv=[sys.argv[0]] + unknown, verbosity=2)

if __name__ == "__main__":
    main()