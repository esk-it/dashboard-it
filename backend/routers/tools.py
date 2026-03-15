"""
Router Tools — Network diagnostic utilities + password generator, IP/CIDR calc,
Wake-on-LAN, WHOIS lookup.
"""
from __future__ import annotations

import asyncio
import ipaddress
import math
import re
import secrets
import socket
import string
import struct
import subprocess
import platform
import time
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/tools", tags=["tools"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class PingRequest(BaseModel):
    host: str
    count: int = 4
    timeout: int = 3

class PingResult(BaseModel):
    host: str
    output: str
    success: bool

class DnsResult(BaseModel):
    host: str
    addresses: list[str]
    aliases: list[str]
    output: str
    success: bool

class TcpTestRequest(BaseModel):
    host: str
    port: int
    timeout: int = 3

class TcpTestResult(BaseModel):
    host: str
    port: int
    open: bool
    latency_ms: int
    output: str


# ── Common ports ──────────────────────────────────────────────────────────────

COMMON_PORTS = [
    {"port": 21, "name": "FTP", "category": "Transfert"},
    {"port": 22, "name": "SSH", "category": "Administration"},
    {"port": 23, "name": "Telnet", "category": "Administration"},
    {"port": 25, "name": "SMTP", "category": "Mail"},
    {"port": 53, "name": "DNS", "category": "Réseau"},
    {"port": 67, "name": "DHCP", "category": "Réseau"},
    {"port": 80, "name": "HTTP", "category": "Web"},
    {"port": 110, "name": "POP3", "category": "Mail"},
    {"port": 135, "name": "RPC", "category": "Windows"},
    {"port": 137, "name": "NetBIOS", "category": "Windows"},
    {"port": 139, "name": "SMB", "category": "Windows"},
    {"port": 143, "name": "IMAP", "category": "Mail"},
    {"port": 161, "name": "SNMP", "category": "Réseau"},
    {"port": 389, "name": "LDAP", "category": "Annuaire"},
    {"port": 443, "name": "HTTPS", "category": "Web"},
    {"port": 445, "name": "SMB/CIFS", "category": "Windows"},
    {"port": 465, "name": "SMTPS", "category": "Mail"},
    {"port": 514, "name": "Syslog", "category": "Réseau"},
    {"port": 587, "name": "SMTP (submission)", "category": "Mail"},
    {"port": 636, "name": "LDAPS", "category": "Annuaire"},
    {"port": 993, "name": "IMAPS", "category": "Mail"},
    {"port": 995, "name": "POP3S", "category": "Mail"},
    {"port": 1433, "name": "MSSQL", "category": "Base de données"},
    {"port": 1521, "name": "Oracle", "category": "Base de données"},
    {"port": 3306, "name": "MySQL", "category": "Base de données"},
    {"port": 3389, "name": "RDP", "category": "Administration"},
    {"port": 5432, "name": "PostgreSQL", "category": "Base de données"},
    {"port": 5900, "name": "VNC", "category": "Administration"},
    {"port": 5985, "name": "WinRM HTTP", "category": "Windows"},
    {"port": 5986, "name": "WinRM HTTPS", "category": "Windows"},
    {"port": 6379, "name": "Redis", "category": "Base de données"},
    {"port": 8080, "name": "HTTP Alt", "category": "Web"},
    {"port": 8443, "name": "HTTPS Alt", "category": "Web"},
    {"port": 9090, "name": "Cockpit", "category": "Administration"},
    {"port": 27017, "name": "MongoDB", "category": "Base de données"},
]


@router.get("/common-ports")
async def get_common_ports():
    return COMMON_PORTS


# ── Ping ──────────────────────────────────────────────────────────────────────

@router.post("/ping", response_model=PingResult)
async def do_ping(data: PingRequest):
    host = data.host.strip()
    if not host:
        return PingResult(host=host, output="Hôte requis", success=False)

    is_win = platform.system().lower() == "windows"
    cmd = ["ping", "-n" if is_win else "-c", str(data.count), "-w" if is_win else "-W",
           str(data.timeout * 1000 if is_win else data.timeout), host]

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=30),
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        return PingResult(host=host, output=output.strip(), success=success)
    except subprocess.TimeoutExpired:
        return PingResult(host=host, output="Timeout (30s)", success=False)
    except Exception as e:
        return PingResult(host=host, output=str(e), success=False)


# ── DNS Lookup ────────────────────────────────────────────────────────────────

@router.post("/dns", response_model=DnsResult)
async def do_dns(host: str = Query(...)):
    host = host.strip()
    if not host:
        return DnsResult(host=host, addresses=[], aliases=[], output="Hôte requis", success=False)

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, socket.gethostbyname_ex, host)
        hostname, aliases, addresses = result
        lines = [f"Hostname: {hostname}"]
        if aliases:
            lines.append(f"Aliases: {', '.join(aliases)}")
        lines.append(f"Addresses: {', '.join(addresses)}")
        return DnsResult(
            host=host, addresses=addresses, aliases=aliases,
            output="\n".join(lines), success=True,
        )
    except socket.gaierror as e:
        return DnsResult(host=host, addresses=[], aliases=[],
                         output=f"DNS lookup failed: {e}", success=False)
    except Exception as e:
        return DnsResult(host=host, addresses=[], aliases=[],
                         output=str(e), success=False)


# ── TCP Port Test ─────────────────────────────────────────────────────────────

@router.post("/tcp", response_model=TcpTestResult)
async def do_tcp_test(data: TcpTestRequest):
    host = data.host.strip()
    port = data.port

    loop = asyncio.get_event_loop()
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(
                None, lambda: socket.create_connection((host, port), timeout=data.timeout).close(),
            ),
            timeout=data.timeout + 1,
        )
        ms = int((time.monotonic() - t0) * 1000)
        return TcpTestResult(
            host=host, port=port, open=True, latency_ms=ms,
            output=f"Port {port} ouvert sur {host} ({ms} ms)",
        )
    except (socket.timeout, asyncio.TimeoutError):
        return TcpTestResult(
            host=host, port=port, open=False, latency_ms=0,
            output=f"Port {port} fermé sur {host} (timeout)",
        )
    except ConnectionRefusedError:
        return TcpTestResult(
            host=host, port=port, open=False, latency_ms=0,
            output=f"Port {port} fermé sur {host} (connexion refusée)",
        )
    except Exception as e:
        return TcpTestResult(
            host=host, port=port, open=False, latency_ms=0,
            output=f"Erreur: {e}",
        )


# ── Traceroute ────────────────────────────────────────────────────────────────

class TracerouteResult(BaseModel):
    host: str
    output: str
    success: bool

@router.post("/traceroute", response_model=TracerouteResult)
async def do_traceroute(host: str = Query(...)):
    host = host.strip()
    is_win = platform.system().lower() == "windows"
    cmd = ["tracert", "-d", "-w", "2000", host] if is_win else ["traceroute", "-n", "-w", "2", host]

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=60),
        )
        output = result.stdout + result.stderr
        return TracerouteResult(host=host, output=output.strip(), success=result.returncode == 0)
    except subprocess.TimeoutExpired:
        return TracerouteResult(host=host, output="Timeout (60s)", success=False)
    except Exception as e:
        return TracerouteResult(host=host, output=str(e), success=False)


# ── Password Generator ───────────────────────────────────────────────────────

class PasswordRequest(BaseModel):
    length: int = 16
    uppercase: bool = True
    lowercase: bool = True
    digits: bool = True
    symbols: bool = True
    exclude_similar: bool = False
    count: int = 1

class PasswordEntry(BaseModel):
    password: str
    strength: str
    entropy: float

class PasswordResponse(BaseModel):
    passwords: list[PasswordEntry]


def _calc_entropy(password: str, pool_size: int) -> float:
    if pool_size <= 1:
        return 0.0
    return len(password) * math.log2(pool_size)


def _strength_label(entropy: float) -> str:
    if entropy < 40:
        return "Faible"
    elif entropy < 60:
        return "Moyen"
    elif entropy < 80:
        return "Fort"
    return "Très fort"


@router.post("/password-generate", response_model=PasswordResponse)
async def generate_passwords(data: PasswordRequest):
    length = max(4, min(128, data.length))
    count = max(1, min(20, data.count))

    charset = ""
    if data.uppercase:
        charset += string.ascii_uppercase
    if data.lowercase:
        charset += string.ascii_lowercase
    if data.digits:
        charset += string.digits
    if data.symbols:
        charset += "!@#$%^&*()-_=+[]{}|;:,.<>?"

    if data.exclude_similar:
        charset = charset.translate(str.maketrans("", "", "Il1O0o"))

    if not charset:
        charset = string.ascii_letters + string.digits

    pool_size = len(charset)
    passwords = []
    for _ in range(count):
        pw = "".join(secrets.choice(charset) for _ in range(length))
        ent = _calc_entropy(pw, pool_size)
        passwords.append(PasswordEntry(password=pw, strength=_strength_label(ent), entropy=round(ent, 1)))

    return PasswordResponse(passwords=passwords)


# ── IP / CIDR Calculator ─────────────────────────────────────────────────────

class IpCalcRequest(BaseModel):
    cidr: str

class SubnetSplit(BaseModel):
    network: str
    first_host: str
    last_host: str
    hosts: int

class IpCalcResponse(BaseModel):
    network: str
    netmask: str
    wildcard: str
    broadcast: str
    prefix: int
    total_addresses: int
    usable_hosts: int
    first_host: str
    last_host: str
    is_private: bool
    ip_class: str
    subnets: list[SubnetSplit]
    success: bool
    error: str = ""


def _ip_class(net: ipaddress.IPv4Network) -> str:
    first = int(net.network_address)
    fb = (first >> 24) & 0xFF
    if fb < 128:
        return "A"
    elif fb < 192:
        return "B"
    elif fb < 224:
        return "C"
    elif fb < 240:
        return "D (Multicast)"
    return "E (Réservé)"


@router.post("/ip-calc", response_model=IpCalcResponse)
async def ip_calc(data: IpCalcRequest):
    try:
        net = ipaddress.ip_network(data.cidr.strip(), strict=False)
    except ValueError as e:
        return IpCalcResponse(
            network="", netmask="", wildcard="", broadcast="", prefix=0,
            total_addresses=0, usable_hosts=0, first_host="", last_host="",
            is_private=False, ip_class="", subnets=[], success=False, error=str(e),
        )

    hosts = list(net.hosts())
    first_host = str(hosts[0]) if hosts else str(net.network_address)
    last_host = str(hosts[-1]) if hosts else str(net.network_address)
    wildcard = str(ipaddress.IPv4Address(int(ipaddress.IPv4Address("255.255.255.255")) ^ int(net.netmask)))

    # Subnet splits: next 3 prefix lengths
    subnets = []
    for extra in range(1, 4):
        new_prefix = net.prefixlen + extra
        if new_prefix > 30:
            break
        subs = list(net.subnets(prefixlen_diff=extra))
        for s in subs[:16]:  # limit to 16 entries
            s_hosts = list(s.hosts())
            subnets.append(SubnetSplit(
                network=str(s),
                first_host=str(s_hosts[0]) if s_hosts else "",
                last_host=str(s_hosts[-1]) if s_hosts else "",
                hosts=len(s_hosts),
            ))
        break  # only first split level

    return IpCalcResponse(
        network=str(net.network_address),
        netmask=str(net.netmask),
        wildcard=wildcard,
        broadcast=str(net.broadcast_address),
        prefix=net.prefixlen,
        total_addresses=net.num_addresses,
        usable_hosts=max(0, net.num_addresses - 2),
        first_host=first_host,
        last_host=last_host,
        is_private=net.is_private,
        ip_class=_ip_class(net) if isinstance(net, ipaddress.IPv4Network) else "N/A",
        subnets=subnets,
        success=True,
    )


# ── Wake-on-LAN ──────────────────────────────────────────────────────────────

class WolRequest(BaseModel):
    mac_address: str
    broadcast_ip: str = "255.255.255.255"
    port: int = 9

class WolResponse(BaseModel):
    success: bool
    message: str


@router.post("/wol", response_model=WolResponse)
async def send_wol(data: WolRequest):
    mac = data.mac_address.strip().upper()
    mac = re.sub(r"[^0-9A-F]", "", mac)

    if len(mac) != 12:
        return WolResponse(success=False, message="Adresse MAC invalide (12 caractères hex attendus)")

    try:
        mac_bytes = bytes.fromhex(mac)
        magic = b"\xff" * 6 + mac_bytes * 16

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: _send_udp(magic, data.broadcast_ip, data.port))

        formatted = ":".join(mac[i:i+2] for i in range(0, 12, 2))
        return WolResponse(success=True, message=f"Magic packet envoyé à {formatted} via {data.broadcast_ip}:{data.port}")
    except Exception as e:
        return WolResponse(success=False, message=f"Erreur: {e}")


def _send_udp(payload: bytes, broadcast: str, port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(payload, (broadcast, port))
    sock.close()


# ── WHOIS Lookup ──────────────────────────────────────────────────────────────

class WhoisRequest(BaseModel):
    query: str

class WhoisResponse(BaseModel):
    query: str
    result: str
    success: bool


def _whois_query(query: str, server: str = "whois.iana.org", port: int = 43) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect((server, port))
    sock.sendall((query + "\r\n").encode())
    response = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk
    sock.close()
    return response.decode("utf-8", errors="replace")


def _extract_refer(text: str) -> Optional[str]:
    for line in text.splitlines():
        if line.lower().startswith("refer:"):
            return line.split(":", 1)[1].strip()
    return None


@router.post("/whois", response_model=WhoisResponse)
async def whois_lookup(data: WhoisRequest):
    query = data.query.strip()
    if not query:
        return WhoisResponse(query=query, result="Requête vide", success=False)

    loop = asyncio.get_event_loop()
    try:
        # First query IANA
        iana_result = await loop.run_in_executor(None, _whois_query, query)
        refer = _extract_refer(iana_result)

        if refer:
            # Follow referral to the specific registrar
            result = await loop.run_in_executor(None, _whois_query, query, refer)
            return WhoisResponse(query=query, result=result.strip(), success=True)
        else:
            return WhoisResponse(query=query, result=iana_result.strip(), success=True)
    except socket.timeout:
        return WhoisResponse(query=query, result="Timeout lors de la connexion WHOIS", success=False)
    except Exception as e:
        return WhoisResponse(query=query, result=f"Erreur: {e}", success=False)
