from multiprocessing import Process, Pipe


def f(conn):
    # sends data to the reciever
    conn.send([42, None, "Hello"])
    conn.send([84, None, "There"])
    # once the connection closes, we cannot send more data
    conn.close()


def main():
    parent_conn, child_conn = Pipe()
    process = Process(target=f, args=(child_conn,))
    process.start()

    # we must have a receive method for each send that is executed
    print(parent_conn.recv())
    print(parent_conn.recv())

    # waits until the child process finishes
    process.join()
