import threading as mp
import logging
import socket
import time
import json
import traceback

from . import message_handlers as mh

logger = logging.getLogger()
#logger = mp.log_to_stderr(logging.DEBUG)
#mp.log_to_stderr(logging.INFO)


class Server:

    def __init__(self, port, com_procs=8, work_procs=4,
                 query_processor_path=None,
                 morph_path=None, morph_port=None,
                 clir_results_dir=None,
                 data_dir=None,
                 summarizaton_config=None,
                 search_config=None,
                 work_dir=None,
                 summary_evidence_dir=None,
                 source_evidence_dir=None):
        self._port = port
        self._com_procs = com_procs
        self._work_procs = work_procs
        self._system_context = {
#?            "query_processor": query_processor_path,
#?            "morph_path": morph_path,
#?            "morph_port": morph_port,
#?            "clir_results_dir": clir_results_dir,
#?            "data_dir": data_dir,
#?            "summarization": summarizaton_config,
#?            "search": search_config,
#?            "work_dir": work_dir,
#?            "summary_evidence_dir": summary_evidence_dir,
#?            "source_evidence_dir": source_evidence_dir,
        }

    @property
    def port(self):
        return self._port

    def start(self):
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind(('',self.port))
        serversocket.listen(5)

        while True:
            try:
                client, address = serversocket.accept()
            except KeyboardInterrupt as ke:
                print("Shutting down...")
                serversocket.shutdown(1)
                serversocket.close()
                break
            logger.debug("{u} connected".format(u=address))
            try:   
                data = client.recv(1000000)
                params = json.loads(data.decode("utf8"))
                print(params)

                if params["message_type"] == "query": 
                    mh.collect_clir_query_results_evidence(
                        params["message_data"], self._system_context)
                elif params["message_type"] == "reload_module":
                    import importlib
                    module = params["message_data"]["module"]
                    print("Reloading module:", module)
                    eval("importlib.reload(importlib.import_module(\"{}\"))".format(module))
                    print("done!")

                client.send(b"OK")
                client.close()
            except Exception as e:
                print("\n")
                traceback.print_exc()
                client.send(b"ERROR")
                client.close()
            
       


#        workers = [
#            mp.Thread(target=worker, args=(serversocket,))
#            for i in range(self._com_procs)
#        ]
#
#        for p in workers:
#            p.daemon = True
#            p.start()
#
#        while True:
#            try:
#                time.sleep(10)
#            except:
#                break
#        for p in 

def worker(socket):
    while True:
        client, address = socket.accept()
        logger.debug("{u} connected".format(u=address))
        try:   
            data = client.recv(1000000)
            params = json.loads(data.decode("utf8"))
            if params["message_type"] == "query": 
                
                mh.collect_clir_query_result_evidence(
                    params["message_data"], {})       

            client.send(b"OK")
            client.close()
        except Exception as e:
            print("\n")
            traceback.print_exc()
            client.send(b"ERROR")


