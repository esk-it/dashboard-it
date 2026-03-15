"""Test guacd with single-socket full handshake."""
import asyncio

def encode(*args):
    return ",".join(f"{len(str(a))}.{a}" for a in args) + ";"

def parse(data):
    parts = []
    i = 0
    data = data.rstrip(";")
    while i < len(data):
        dot = data.find(".", i)
        if dot < 0: break
        length = int(data[i:dot])
        value = data[dot+1:dot+1+length]
        parts.append(value)
        i = dot+1+length
        if i < len(data) and data[i] == ",": i += 1
    return parts

async def read_instruction(reader, timeout=5):
    buf = b""
    while b";" not in buf:
        chunk = await asyncio.wait_for(reader.read(4096), timeout=timeout)
        if not chunk: return ""
        buf += chunk
    return buf[:buf.index(b";")+1].decode()

async def test():
    r, w = await asyncio.open_connection("127.0.0.1", 4822)

    # Step 1: select rdp
    w.write(encode("select", "rdp").encode())
    await w.drain()

    # Step 2: read args
    args_data = await read_instruction(r)
    param_names = parse(args_data)[1:]
    print(f"Got {len(param_names)} args")

    # Step 3: send size, audio, video, image BEFORE connect
    for instr in [
        encode("size", "1920", "1080", "96"),
        encode("audio"),
        encode("video"),
        encode("image", "image/png", "image/jpeg", "image/webp"),
        encode("timezone", "Europe/Paris"),
    ]:
        print(f"Sending: {instr}")
        w.write(instr.encode())
    await w.drain()

    # Step 4: send connect
    param_values = {
        "VERSION_1_5_0": "VERSION_1_5_0",
        "hostname": "192.168.1.12", "port": "3389",
        "username": "Johann", "password": "",
        "width": "1920", "height": "1080", "dpi": "96",
        "color-depth": "32", "resize-method": "display-update",
        "security": "nla", "ignore-cert": "true",
        "enable-theming": "true", "enable-font-smoothing": "true",
    }
    values = ["connect"] + [param_values.get(n, "") for n in param_names]
    connect_instr = encode(*values)
    print(f"Connect: {connect_instr[:200]}...")
    w.write(connect_instr.encode())
    await w.drain()

    # Step 5: read ready
    ready = await read_instruction(r, timeout=15)
    print(f"Ready: {ready[:100]}")

    # Step 6: read display data
    print("\n=== Reading display data ===")
    total = 0
    try:
        for i in range(30):
            chunk = await asyncio.wait_for(r.read(65536), timeout=15)
            if not chunk:
                print(f"EOF after {total} bytes")
                break
            total += len(chunk)
            text = chunk.decode(errors='replace')
            if i < 5:
                print(f"CHUNK {i}: {len(chunk)} bytes - {text[:200]}")
            else:
                print(f"CHUNK {i}: {len(chunk)} bytes")
    except asyncio.TimeoutError:
        print(f"Timeout after {total} total bytes")

    w.close()

asyncio.run(test())
